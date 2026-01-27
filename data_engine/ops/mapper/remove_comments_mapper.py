# Some code here has been modified from:
# https://github.com/togethercomputer/RedPajama-Data/tree/rp_v1/
# --------------------------------------------------------

from typing import List, Union

import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('remove_comments_mapper')
class RemoveCommentsMapper(Mapper):
    """
    Mapper to remove comments in different kinds of documents.

    Only support 'tex' for now.
    """

    def __init__(self,
                 doc_type: Union[str, List[str]] = 'tex',
                 inline: bool = True,
                 multiline: bool = True,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param doc_type: Type of document to remove comments.
        :param inline: Whether to remove inline comments.
        :param multiline: Whether to remove multiline comments.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.doc_type = doc_type
        self.inline = inline
        self.multiline = multiline
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def process(self, sample):
        # Track statistics
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        
        original_text = sample[self.text_key]
        
        # TODO: remove different comments by sample type

        if self.inline:
            # remove all in comments within a line
            sample[self.text_key] = re.sub(pattern=r'[^\\]%.+$',
                                           repl=r'',
                                           string=sample[self.text_key],
                                           flags=re.MULTILINE)

        if self.multiline:
            sample[self.text_key] = re.sub(pattern=r'(?m)^%.*\n?',
                                           repl=r'',
                                           string=sample[self.text_key],
                                           flags=re.MULTILINE)
        
        # Track if modified
        if getattr(self, 'enable_detailed_logging', False):
            if sample[self.text_key] != original_text:
                self.modified_samples += 1
            else:
                self.unmodified_samples += 1
        
        return sample

    @classmethod
    @property
    def description(cls):
        return     """
    Mapper to remove comments in different kinds of documents.

    Only support 'tex' for now.
    """

    @classmethod
    @property
    def sample(cls):
        return Sample("%%\n%% This is file `sample-sigconf.tex',\n%% The first command in your LaTeX source must be the \\documentclass command.\n\\documentclass[sigconf,review,anonymous]{acmart}\n%% NOTE that a single column version is required for \n%% submission and peer review. This can be done by changing\n\\input{math_commands.tex}\n%% end of the preamble, start of the body of the document source.\n\\begin{document}\n%% The \"title\" command has an optional parameter,\n\\title{Hierarchical Cross Contrastive Learning of Visual Representations}\n%%\n%% The \"author\" command and its associated commands are used to define\n%% the authors and their affiliations.\n\\author{Hesen Chen}\n\\affiliation{%\n  \\institution{Alibaba Group}\n  \\city{Beijing}\n  \\country{China}}\n\\email{hesen.chs@alibaba-inc.com}\n%% By default, the full list of authors will be used in the page\n\\begin{abstract}The rapid\n\\end{abstract}\n\\begin{CCSXML}\n\\ccsdesc[500]{Computing methodologies~Image representations}\n%% Keywords. The author(s) should pick words that accurately describe\n\\keywords{self-supervised,  ontrastive Learning, hierarchical projection, cross-level}\n%% page.\n\\begin{teaserfigure}\n\\end{teaserfigure}\n%% This command processes the author and affiliation and title\n\\maketitle\n\\section{Introduction}\n\\begin{itemize}\n\\end{itemize}\n\\section{Related Work}\n\\label{gen_inst} Self-supervised\n\\section{Method}\n\\label{method}In this section,\n\\subsection{Framework} kkk\n\\subsection{Cross Contrastive Loss}\nSince $\\sZ^n$ are extracted\n\\subsection{Implementation details}\n\\textbf{Image augmentations} We use\n\\textbf{Architecture} We use\n\\textbf{Optimization} We adapt \n\\section{Experiments}\n\\label{experiments}In this section\n\\subsection{Linear and Semi-Supervised Evaluations on ImageNet}\n\\textbf{Linear evaluation on ImageNet} We firs\n\\textbf{Semi-supervised learning on ImageNet} We simply\n\\subsection{Transfer to other datasets and tasks}\n\\textbf{Image classification with fixed features} We follow\n\\section{Ablations} We present\n\\subsection{Influence of hierarchical projection head and cross contrastive loss} get out\n\\subsection{Levels and depth of projector network}\n\\end{center}\n\\caption{\\label{figure3} \\textbf{Different way of cross-correlation on 3 level hierarchical projection head.} '=' denotes stop gradient.}\n\\end{figure}\n\\subsection{Analyze of} In this\n\\textbf{Similarity between} Using SimSiam\n\\textbf{Feature similarity} We extracted\n\\section{Conclusion}\nWe propose HCCL\n\\clearpage\n\\bibliographystyle{ACM-Reference-Format}\n\\bibliography{sample-base}\n\\end{document}\n\\endinput\n%%\n%% End of file `sample-sigconf.tex'.\n", 
                      "\\documentclass[sigconf,review,anonymous]{acmart}\n\\input{math_commands.tex}\n\\begin{document}\n\\title{Hierarchical Cross Contrastive Learning of Visual Representations}\n\\author{Hesen Chen}\n\\affiliation{%\n  \\institution{Alibaba Group}\n  \\city{Beijing}\n  \\country{China}}\n\\email{hesen.chs@alibaba-inc.com}\n\\begin{abstract}The rapid\n\\end{abstract}\n\\begin{CCSXML}\n\\ccsdesc[500]{Computing methodologies~Image representations}\n\\keywords{self-supervised,  ontrastive Learning, hierarchical projection, cross-level}\n\\begin{teaserfigure}\n\\end{teaserfigure}\n\\maketitle\n\\section{Introduction}\n\\begin{itemize}\n\\end{itemize}\n\\section{Related Work}\n\\label{gen_inst} Self-supervised\n\\section{Method}\n\\label{method}In this section,\n\\subsection{Framework} kkk\n\\subsection{Cross Contrastive Loss}\nSince $\\sZ^n$ are extracted\n\\subsection{Implementation details}\n\\textbf{Image augmentations} We use\n\\textbf{Architecture} We use\n\\textbf{Optimization} We adapt \n\\section{Experiments}\n\\label{experiments}In this section\n\\subsection{Linear and Semi-Supervised Evaluations on ImageNet}\n\\textbf{Linear evaluation on ImageNet} We firs\n\\textbf{Semi-supervised learning on ImageNet} We simply\n\\subsection{Transfer to other datasets and tasks}\n\\textbf{Image classification with fixed features} We follow\n\\section{Ablations} We present\n\\subsection{Influence of hierarchical projection head and cross contrastive loss} get out\n\\subsection{Levels and depth of projector network}\n\\end{center}\n\\caption{\\label{figure3} \\textbf{Different way of cross-correlation on 3 level hierarchical projection head.} '=' denotes stop gradient.}\n\\end{figure}\n\\subsection{Analyze of} In this\n\\textbf{Similarity between} Using SimSiam\n\\textbf{Feature similarity} We extracted\n\\section{Conclusion}\nWe propose HCCL\n\\clearpage\n\\bibliographystyle{ACM-Reference-Format}\n\\bibliography{sample-base}\n\\end{document}\n\\endinput\n")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("inline", DataType.BOOLEAN, None, True),
            Param("multiline", DataType.BOOLEAN, None, True),
        ]
    
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
            total = self.total_samples
            modified = self.modified_samples
            unmodified = self.unmodified_samples
            if total == 0:
                return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Comments Removal Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with comments removed: {modified} ({modified/total*100:.2f}%)")
            self._log_line(f"Samples unchanged: {unmodified} ({unmodified/total*100:.2f}%)")
            self._log_line("="*60)
        except Exception as e:
            import traceback
            from loguru import logger
            error_msg = f"Failed to generate mapper logging: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)