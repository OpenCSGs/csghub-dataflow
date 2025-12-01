#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF 转 Markdown 功能测试脚本

测试 MinerU 的 PDF 转 Markdown 功能是否正常工作
使用方法：
1. 将 PDF 文件放入 input 文件夹
2. 运行此脚本：python test_pdf_to_markdown.py
3. 检查 output 文件夹中的转换结果
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 颜色输出支持
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_warning(msg: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

def print_info(msg: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")

def print_section(title: str):
    """打印章节标题"""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")


class PDFToMarkdownTester:
    """PDF 转 Markdown 测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        # 获取脚本所在目录
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent.parent
        
        # 设置路径
        self.input_dir = self.script_dir / "input"
        self.output_dir = self.script_dir / "output"
        self.mineru_worker_script = self.project_root / "data_celery" / "formatify" / "mineru_worker.py"
        
        # 确保目录存在
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # 测试结果
        self.test_results: List[Dict] = []
    
    def check_environment(self) -> Tuple[bool, Dict[str, str]]:
        """检查环境配置"""
        print_section("1. 检查环境配置")
        
        env_info = {}
        all_ok = True
        
        # 检查 Python 版本
        python_version = sys.version_info
        env_info['python_version'] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
        print_info(f"Python 版本: {env_info['python_version']}")
        
        # 检查环境变量
        mineru_api_url = os.getenv("MINERU_API_URL", "http://111.4.242.20:30000")
        mineru_backend = os.getenv("MINERU_BACKEND", "http-client")
        
        env_info['MINERU_API_URL'] = mineru_api_url
        env_info['MINERU_BACKEND'] = mineru_backend
        
        print_info(f"MINERU_API_URL: {mineru_api_url}")
        print_info(f"MINERU_BACKEND: {mineru_backend}")
        
        # 检查 mineru_worker.py 是否存在
        if not self.mineru_worker_script.exists():
            print_error(f"mineru_worker.py 不存在: {self.mineru_worker_script}")
            all_ok = False
        else:
            print_success(f"找到 mineru_worker.py: {self.mineru_worker_script}")
        
        # 检查必要的 Python 包
        required_packages = [
            'mineru',
            'dotenv'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print_success(f"已安装: {package}")
            except ImportError:
                print_error(f"未安装: {package}")
                missing_packages.append(package)
                all_ok = False
        
        if all_ok:
            print_success("环境配置检查通过")
        else:
            print_error("环境配置检查失败")
        
        return all_ok, env_info
    
    def find_pdf_files(self) -> List[Path]:
        """查找输入文件夹中的 PDF 文件"""
        print_section("2. 查找 PDF 文件")
        
        pdf_files = list(self.input_dir.glob("*.pdf"))
        
        if not pdf_files:
            print_warning(f"在 {self.input_dir} 中未找到 PDF 文件")
            print_info("请将 PDF 文件放入 input 文件夹后重试")
            return []
        
        print_success(f"找到 {len(pdf_files)} 个 PDF 文件:")
        for pdf_file in pdf_files:
            file_size = pdf_file.stat().st_size / 1024  # KB
            print_info(f"  - {pdf_file.name} ({file_size:.2f} KB)")
        
        return pdf_files
    
    def test_single_pdf(self, pdf_file: Path, env_info: Dict[str, str]) -> Dict:
        """测试单个 PDF 文件的转换"""
        print_section(f"3. 测试转换: {pdf_file.name}")
        
        result = {
            'file': str(pdf_file),
            'filename': pdf_file.name,
            'success': False,
            'error': None,
            'output_file': None,
            'duration': 0,
            'details': {}
        }
        
        start_time = time.time()
        
        try:
            # 准备临时输出目录
            pdf_file_name = pdf_file.stem
            temp_output_dir = self.output_dir / f"_temp_{pdf_file_name}"
            temp_output_dir.mkdir(exist_ok=True)
            
            # 准备结果 JSON 路径
            result_json_path = temp_output_dir / "mineru_result.json"
            
            # 构建命令
            python_exe = sys.executable
            cmd = [
                python_exe,
                str(self.mineru_worker_script),
                str(pdf_file),
                str(temp_output_dir),
                env_info['MINERU_API_URL'],
                env_info['MINERU_BACKEND'],
                str(result_json_path)
            ]
            
            print_info(f"执行命令: {' '.join(cmd)}")
            
            # 执行转换
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root),
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            stdout, stderr = process.communicate()
            
            result['duration'] = time.time() - start_time
            
            # 检查返回码
            if process.returncode != 0:
                error_msg = f"进程返回码: {process.returncode}"
                if stderr:
                    error_msg += f"\n错误输出: {stderr}"
                
                # 尝试读取结果 JSON 获取更详细的错误信息
                if result_json_path.exists():
                    try:
                        with open(result_json_path, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                            if not result_data.get("success", False):
                                error_msg = result_data.get("error", error_msg)
                    except Exception as e:
                        error_msg += f"\n无法读取结果 JSON: {e}"
                
                result['error'] = error_msg
                print_error(f"转换失败: {error_msg}")
                return result
            
            # 检查结果 JSON 文件
            if not result_json_path.exists():
                result['error'] = "结果 JSON 文件不存在"
                print_error("结果 JSON 文件不存在")
                return result
            
            # 读取结果
            with open(result_json_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            
            if not result_data.get("success", False):
                error_msg = result_data.get("error", "未知错误")
                result['error'] = error_msg
                print_error(f"转换失败: {error_msg}")
                return result
            
            # 检查 middle_json
            if "middle_json" not in result_data:
                result['error'] = "结果中缺少 middle_json"
                print_error("结果中缺少 middle_json")
                return result
            
            middle_json = result_data["middle_json"]
            result['details']['middle_json_keys'] = list(middle_json.keys())
            
            # 生成 Markdown 文件
            try:
                from mineru.cli.common import prepare_env
                from mineru.data.data_reader_writer import FileBasedDataWriter
                from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
                from mineru.utils.enum_class import MakeMode
                
                local_image_dir, local_md_dir = prepare_env(str(temp_output_dir), pdf_file_name, "vlm")
                md_writer = FileBasedDataWriter(local_md_dir)
                
                pdf_info = middle_json.get("pdf_info", {})
                image_dir = ""
                md_content_str = vlm_union_make(pdf_info, MakeMode.MM_MD, image_dir)
                
                markdown_filename = f"{pdf_file_name}.md"
                md_writer.write_string(markdown_filename, md_content_str)
                
                markdown_file_path = Path(local_md_dir) / markdown_filename
                final_markdown_path = self.output_dir / markdown_filename
                
                if markdown_file_path.exists():
                    import shutil
                    shutil.move(str(markdown_file_path), str(final_markdown_path))
                    result['output_file'] = str(final_markdown_path)
                    result['success'] = True
                    
                    # 检查输出文件大小
                    output_size = final_markdown_path.stat().st_size
                    result['details']['output_size'] = output_size
                    
                    print_success(f"转换成功！输出文件: {final_markdown_path}")
                    print_info(f"输出文件大小: {output_size} 字节")
                    print_info(f"耗时: {result['duration']:.2f} 秒")
                else:
                    result['error'] = "Markdown 文件生成失败"
                    print_error("Markdown 文件生成失败")
                
            except Exception as e:
                result['error'] = f"生成 Markdown 文件时出错: {str(e)}"
                print_error(f"生成 Markdown 文件时出错: {e}")
                import traceback
                traceback.print_exc()
            
            # 清理临时目录
            try:
                import shutil
                if temp_output_dir.exists():
                    shutil.rmtree(temp_output_dir)
            except Exception as e:
                print_warning(f"清理临时目录失败: {e}")
            
        except Exception as e:
            result['error'] = f"转换过程中出错: {str(e)}"
            result['duration'] = time.time() - start_time
            print_error(f"转换过程中出错: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def run_tests(self):
        """运行所有测试"""
        print_section("PDF 转 Markdown 功能测试")
        print_info(f"项目根目录: {self.project_root}")
        print_info(f"输入目录: {self.input_dir}")
        print_info(f"输出目录: {self.output_dir}")
        
        # 检查环境
        env_ok, env_info = self.check_environment()
        if not env_ok:
            print_error("环境检查失败，请修复环境问题后重试")
            return
        
        # 查找 PDF 文件
        pdf_files = self.find_pdf_files()
        if not pdf_files:
            return
        
        # 测试每个 PDF 文件
        print_section("4. 开始转换测试")
        
        for pdf_file in pdf_files:
            result = self.test_single_pdf(pdf_file, env_info)
            self.test_results.append(result)
        
        # 输出测试总结
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        print_section("5. 测试总结")
        
        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r['success'])
        failed = total - success
        
        print_info(f"总测试数: {total}")
        print_success(f"成功: {success}")
        if failed > 0:
            print_error(f"失败: {failed}")
        
        print("\n详细结果:")
        for i, result in enumerate(self.test_results, 1):
            status = "✓" if result['success'] else "✗"
            color = Colors.GREEN if result['success'] else Colors.RED
            print(f"{color}{status} [{i}/{total}] {result['filename']}{Colors.RESET}")
            
            if result['success']:
                print(f"  输出文件: {result['output_file']}")
                print(f"  耗时: {result['duration']:.2f} 秒")
                if 'output_size' in result['details']:
                    print(f"  输出大小: {result['details']['output_size']} 字节")
            else:
                print(f"  错误: {result['error']}")
                if 'duration' in result and result['duration'] > 0:
                    print(f"  耗时: {result['duration']:.2f} 秒")
            print()
        
        # 诊断信息
        if failed > 0:
            self.print_diagnosis()
    
    def print_diagnosis(self):
        """打印诊断信息"""
        print_section("6. 问题诊断")
        
        failed_results = [r for r in self.test_results if not r['success']]
        
        print_warning("失败的测试分析:")
        for result in failed_results:
            print(f"\n文件: {result['filename']}")
            print(f"错误: {result['error']}")
            
            error_msg = result['error'].lower() if result['error'] else ""
            
            # 常见错误诊断
            if "unsupported backend" in error_msg:
                print_info("诊断: MinerU API 服务器不支持指定的 backend")
                print_info("建议: 检查 MINERU_BACKEND 环境变量，确保使用支持的 backend")
                print_info("支持的 backend: transformers, sglang-engine, sglang-client, http-client")
            
            elif "connection" in error_msg or "timeout" in error_msg:
                print_info("诊断: 无法连接到 MinerU API 服务器")
                print_info("建议: 检查 MINERU_API_URL 环境变量和网络连接")
            
            elif "no such file" in error_msg or "file not found" in error_msg:
                print_info("诊断: 文件路径问题")
                print_info("建议: 检查输入文件是否存在且可读")
            
            elif "import" in error_msg or "module" in error_msg:
                print_info("诊断: Python 模块导入失败")
                print_info("建议: 检查是否安装了 mineru 包及其依赖")
            
            elif "permission" in error_msg:
                print_info("诊断: 文件权限问题")
                print_info("建议: 检查文件读写权限")
            
            else:
                print_info("诊断: 未知错误，请查看详细错误信息")


def main():
    """主函数"""
    tester = PDFToMarkdownTester()
    tester.run_tests()


if __name__ == '__main__':
    main()

