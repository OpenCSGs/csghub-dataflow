# Some code here has been modified from:
# https://github.com/togethercomputer/RedPajama-Data/blob/rp_v1/data_prep/arxiv/arxiv_cleaner.py
# --------------------------------------------------------

import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('expand_macro_mapper')
class ExpandMacroMapper(Mapper):
    """Mapper to expand macro definitions in the document body of Latex
    samples."""

    def __init__(self, *args, **kwargs):
        """
        Initialization method.

        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def _build_non_arg_macros_dict(self, file_content):
        # regex for extracting \newcommand macros without arguments
        non_arg_nc_reg = re.compile(
            # this regex matches the following:
            # \newcommand{\macro_name}{macro_value}
            # \newcommand*{\macro_name}{macro_value}
            # where macro_name is only allowed to contain letters and numbers;
            # macro_value can contain any character.
            pattern=r'\\\bnewcommand\b\*?\{(\\[a-zA-Z0-9]+?)\}\{(.*?)\}$',
            flags=re.MULTILINE)

        # regex for extracting \def macros without arguments
        non_arg_def_reg = re.compile(
            # this regex matches the following:
            # \def\macro_name{macro_value}
            # where macro_name is only allowed to contain letters and numbers;
            # macro_value can contain any character.
            pattern=r'\\def\s*(\\[a-zA-Z0-9]+?)\s*\{(.*?)\}$',
            flags=re.MULTILINE)

        # Extract all user-defined LaTeX macros from the preamble
        macros = {}
        for reg in [non_arg_nc_reg, non_arg_def_reg]:
            for match in reg.finditer(file_content):
                # convert the macro name and value to a raw string that can be
                # used in re.sub
                macro_name = match.group(1).encode('unicode-escape').decode(
                    'utf-8')
                macro_val = match.group(2).encode('unicode-escape').decode(
                    'utf-8')

                macros[macro_name] = macro_val
        return macros

    def process(self, sample):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        original_text = sample[self.text_key]
        
        non_arg_macros = self._build_non_arg_macros_dict(sample[self.text_key])

        # TODO: macros that take arguments are not supported yet
        arg_macros = {}

        # inline-expand all non-arg macros
        for macro_name, macro_value in non_arg_macros.items():
            sample[self.text_key] = re.sub(
                # make pattern grouped to make sure that the macro is not part
                # of a longer alphanumeric word
                pattern=r'(' + macro_name + r')' + r'([^a-zA-Z0-9])',
                # replace the macro with its value and add back the character
                # that was matched after the macro
                repl=macro_value + r'\2',
                string=sample[self.text_key])

        # inline-expand all macros that use args
        # TODO: inline-expand macros with args
        for macro_name, macro_value in arg_macros.items():
            pass

        if getattr(self, 'enable_detailed_logging', False):
            if sample[self.text_key] != original_text:
                self.modified_samples += 1
            else:
                self.unmodified_samples += 1
        return sample


    @classmethod
    @property
    def description(cls):
        return """Mapper to expand macro definitions in the document body of Latex
    samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample('\\documentclass{article}\n% Recommended, but optional, packages for figures and better typesetting:\n\\usepackage{microtype}\n\\usepackage{graphicx}\n\n% Attempt to make hyperref and algorithmic work together better:\n\\newcommand{\\theHalgorithm}{\\arabic{algorithm}}\n% For theorems and such\n\\usepackage{amsmath}\n\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n% THEOREMS\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n\\theoremstyle{plain}\n\\newtheorem{lemma}[theorem]{Lemma}\n\\newtheorem{corollary}[theorem]{Corollary}\n\\theoremstyle{definition}\n\n\\usepackage[textsize=small]{todonotes}\n\\setuptodonotes{inline}\n\n\\usepackage{makecell}\n\\newcommand{\\cmark}{\\ding{51}\\xspace}%\n\\newcommand{\\xmark}{\\ding{55}\\xspace}%\n\n\\def \\alambic {\\includegraphics[height=1.52ex]{img/alembic-crop.pdf}\\xspace}\n\n\\newcommand\\binke[1]{{\\color{blue} \\footnote{\\color{blue}binke: #1}} }\n\\newcommand\\Zerocost{Zero-cost}\n\\newcommand\\imagenet{ImageNet}\n\n\\begin{document}\n\n\\begin{abstract}\nThe wide\n\\end{abstract}\n\\section{Introduction}\n\\label{introduction}\nThe main contributions are summarized as follows:\n\\section{Background and Related Work}\\label{background}\n\\subsection{One-Shot NAS} In one-shot NAS\n\\section{PreNAS}\\label{method}In this\n\\subsection{One-Shot NAS with Preferred Learning}\nIn the specialization stage, the optimal architectures under given  resource constraints can be directly obtained:\n\\begin{equation}\n\\widetilde{\\mathcal{A}}^* = \\widetilde{\\mathcal{A}} .\n\\end{equation}\n\\subsection{Zero-Cost Transformer Selector}\\label{sub:layerNorm}\n\\subsection{Performance Balancing} We discuss\n\\section{Experiments}\\label{experiments}\n\\subsection{Setup}\n\\subsection{Main Results}\\label{sec:sota}\n\\subsection{Analysis and Ablation study}\\label{ablation}\n\\begin{figure}[t]\n\\vskip 0.1in\n    \\centering\n    \\subfigure[Search spaces]{\\includegraphics[width=0.36\\linewidth]{img/search_space.pdf}\\label{fg:search_space:a}}%\n    \\hfil%\n    \\subfigure[Error distributions]{\\includegraphics[width=0.58\\linewidth]{img/cumulation.pdf}\\label{fg:search_space:b}}\n    \\caption{Model quality}\n\\vskip -0.1in\n\\end{figure}\n\\paragraph{Effect of Performance Balancing} During\n\\subsection{Transfer Learning Results}\n\\subsection{CNN Results} in terms of similar FLOPs.\n\\FloatBarrier\n\\section{Conclusion}\\label{conclusion} In this\n% Acknowledgements should only appear in the accepted version.\n\\bibliography{ref}\n\\bibliographystyle{icml2023}\n\\clearpage\n\\appendix\n\\onecolumn\n\\section{Statistical}\n\\label{appendix:snipAnalysis} We analyze\n\\section{The Greedy Algorithm}\n\\label{appendix:greedy}\n\\section{Regularization \\& Data Augmentation}\\label{appendix:aug}\n\\renewcommand{\\arraystretch}{1.2}\n\\end{document}\n', 
                      "\\documentclass{article}\n% Recommended, but optional, packages for figures and better typesetting:\n\\usepackage{microtype}\n\\usepackage{graphicx}\n\n% Attempt to make hyperref and algorithmic work together better:\n\\newcommand{\\arabic{algorithm}}{\\arabic{algorithm}}\n% For theorems and such\n\\usepackage{amsmath}\n\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n% THEOREMS\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n\\theoremstyle{plain}\n\\newtheorem{lemma}[theorem]{Lemma}\n\\newtheorem{corollary}[theorem]{Corollary}\n\\theoremstyle{definition}\n\n\\usepackage[textsize=small]{todonotes}\n\\setuptodonotes{inline}\n\n\\usepackage{makecell}\n\\newcommand{\\cmark}{\\ding{51}\\xspace}%\n\\newcommand{\\xmark}{\\ding{55}\\xspace}%\n\n\\def \\includegraphics[height=1.52ex]{img/alembic-crop.pdf}\\xspace {\\includegraphics[height=1.52ex]{img/alembic-crop.pdf}\\xspace}\n\n\\newcommand\\binke[1]{{\\color{blue} \\footnote{\\color{blue}binke: #1}} }\n\\newcommand\\Zerocost{Zero-cost}\n\\newcommand\\imagenet{ImageNet}\n\n\\begin{document}\n\n\\begin{abstract}\nThe wide\n\\end{abstract}\n\\section{Introduction}\n\\label{introduction}\nThe main contributions are summarized as follows:\n\\section{Background and Related Work}\\label{background}\n\\subsection{One-Shot NAS} In one-shot NAS\n\\section{PreNAS}\\label{method}In this\n\\subsection{One-Shot NAS with Preferred Learning}\nIn the specialization stage, the optimal architectures under given  resource constraints can be directly obtained:\n\\begin{equation}\n\\widetilde{\\mathcal{A}}^* = \\widetilde{\\mathcal{A}} .\n\\end{equation}\n\\subsection{Zero-Cost Transformer Selector}\\label{sub:layerNorm}\n\\subsection{Performance Balancing} We discuss\n\\section{Experiments}\\label{experiments}\n\\subsection{Setup}\n\\subsection{Main Results}\\label{sec:sota}\n\\subsection{Analysis and Ablation study}\\label{ablation}\n\\begin{figure}[t]\n\\vskip 0.1in\n    \\centering\n    \\subfigure[Search spaces]{\\includegraphics[width=0.36\\linewidth]{img/search_space.pdf}\\label{fg:search_space:a}}%\n    \\hfil%\n    \\subfigure[Error distributions]{\\includegraphics[width=0.58\\linewidth]{img/cumulation.pdf}\\label{fg:search_space:b}}\n    \\caption{Model quality}\n\\vskip -0.1in\n\\end{figure}\n\\paragraph{Effect of Performance Balancing} During\n\\subsection{Transfer Learning Results}\n\\subsection{CNN Results} in terms of similar FLOPs.\n\\FloatBarrier\n\\section{Conclusion}\\label{conclusion} In this\n% Acknowledgements should only appear in the accepted version.\n\\bibliography{ref}\n\\bibliographystyle{icml2023}\n\\clearpage\n\\appendix\n\\onecolumn\n\\section{Statistical}\n\\label{appendix:snipAnalysis} We analyze\n\\section{The Greedy Algorithm}\n\\label{appendix:greedy}\n\\section{Regularization \\& Data Augmentation}\\label{appendix:aug}\n\\renewcommand{\\arraystretch}{1.2}\n\\end{document}\n")

    @classmethod
    @property
    def init_params(cls):
        return None
    
    def run(self, dataset, *, exporter=None, tracer=None):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples = 0
            self.modified_samples = 0
            self.unmodified_samples = 0
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        return result
    
    def _log_mapper_summary(self):
        try:
            from loguru import logger
            total, modified, unmodified = self.total_samples, self.modified_samples, self.unmodified_samples
            if total == 0: return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Expand Macro Summary")
            self._log_line("="*60)
            self._log_line(f"Total: {total}, Expanded: {modified} ({modified/total*100:.2f}%), Unchanged: {unmodified} ({unmodified/total*100:.2f}%)")
            self._log_line("="*60)
        except: pass
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)