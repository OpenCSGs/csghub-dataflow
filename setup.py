import logging
import os.path
import re

import setuptools


# def get_package_dir():
#     pkg_dir = {
#         'data_juicer.tools': 'tools',
#         'data_juicer.tools.legacies': 'legacies',
#     }
#     return pkg_dir


def get_install_requirements(require_f_paths, env_dir='environments'):
    reqs = []
    for path in require_f_paths:
        target_f = os.path.join(env_dir, path)
        if not os.path.exists(target_f):
            logging.warning(f'target file does not exist: {target_f}')
        else:
            with open(target_f, 'r', encoding='utf-8') as fin:
                reqs += [x.strip() for x in fin.read().splitlines()]
    reqs = [x for x in reqs if not x.startswith('#')]
    return reqs


# allowing selective installment based on users' needs
# TODO: The specific taxonomy and dependencies will be determined
#  after implementing some preliminary operators and detailed discussions
min_requires = get_install_requirements(['minimal_requires.txt'])
extra_requires = {
    'mini':
    min_requires,
    'sci':
    get_install_requirements(['science_requires.txt']),
    'dist':
    get_install_requirements(['dist_requires.txt']),
    'dev':
    get_install_requirements(['dev_requires.txt']),
    'tools':
    get_install_requirements(
        ['preprocess_requires.txt', 'quality_classifier_requires.txt']),
}
extra_requires['all'] = [v for v in extra_requires.values()]
extra_requires['sandbox'] = get_install_requirements(['sandbox_requires.txt'])
version = '2024-12'

with open('README.md', encoding='utf-8') as f:
    readme_md = f.read()

setuptools.setup(
    name='py-data-flow',
    version=version,
    url='https://opencsg.com/datapipelines',
    author='opencsg',
    description='A One-Stop Data Processing System for Large Language Models.',
    long_description=readme_md,
    long_description_content_type='text/markdown',
    license='Comercial',
    packages=setuptools.find_packages(exclude=['tests*']),
    entry_points={
        'console_scripts': [
            'df-process = tool_legacy.process_data:main',
            'df-analyze = tool_legacy.analyze_data:main',
            'df-server = data_server.app:serve',
        ]
    },
    install_requires=min_requires,
    extras_require=extra_requires,
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent'
    ],
)
