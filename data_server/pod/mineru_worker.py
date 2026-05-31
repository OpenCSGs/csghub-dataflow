#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone MinerU worker script.
Runs MinerU in a separate process to avoid blocking the main process.
"""
import sys
import json
from pathlib import Path


def main():
    """Read config from CLI args and run MinerU conversion."""
    if len(sys.argv) < 6:
        print("Usage: python mineru_worker.py <pdf_file_path> <temp_output_dir> <server_url> <backend> <result_json_path>", file=sys.stderr)
        sys.exit(1)
    
    pdf_file_path = sys.argv[1]
    temp_output_dir = sys.argv[2]
    server_url = sys.argv[3]
    backend = sys.argv[4]
    result_json_path = sys.argv[5]
    
    try:
        from mineru.cli.common import read_fn, prepare_env
        from mineru.data.data_reader_writer import FileBasedDataWriter
        from mineru.backend.vlm.vlm_analyze import doc_analyze as vlm_doc_analyze
        
        pdf_bytes = read_fn(Path(pdf_file_path))
        pdf_file_name = Path(pdf_file_path).stem
        
        local_image_dir, local_md_dir = prepare_env(temp_output_dir, pdf_file_name, "vlm")
        image_writer = FileBasedDataWriter(local_image_dir)
        
        middle_json, _ = vlm_doc_analyze(
            pdf_bytes,
            image_writer=image_writer,
            backend=backend,
            server_url=server_url
        )
        
        result = {
            "success": True,
            "middle_json": middle_json
        }
        
        with open(result_json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, default=str)
        
        sys.exit(0)
        
    except Exception as e:
        result = {
            "success": False,
            "error": str(e)
        }
        
        try:
            with open(result_json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False)
        except:
            pass
        
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

