from dataclasses import dataclass
from data_server.logic.models import Recipe, Tool
from typing import Union, Literal, Optional
import pathlib
import os
import glob
import yaml
from typing import Annotated
import random


SAMPLE_DIR = 'configs/samples'

class Plan:
    dataset: str
    sub_dataset: Optional[str] = None
    readme: Optional[str] = None
    tools_ordered: Optional[list[Tool]] = []
    recipe: Recipe
    category: Union[Literal["refine"], Literal["reproduced"]]

def load_samples():

    def recursive_glob(pattern, root='.'):
        matches = []
        for dirpath, dirnames, filenames in os.walk(root):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if glob.fnmatch.fnmatch(filepath, pattern):
                    matches.append(filepath)
        return matches
    
    base_dir = pathlib.Path().resolve()
    sample_path = os.path.join(base_dir, SAMPLE_DIR)
    # print(f"loading samples from path: {sample_path}")

    def parse(path: str):
        separator = "\\" if os.name == "nt" else "/"
        raw_items = path.split(separator)
        assert len(raw_items) == 3

        category = "refine" if "refine" in raw_items[0] else "reproduced"
        dataset = raw_items[1]
        sub_dataset = raw_items[2].replace(category, "").replace(dataset, "").strip("-")
        return category, dataset, sub_dataset

    file_list = sorted(recursive_glob("*.yaml", sample_path))
    plans: list[Plan] = []
    for file in file_list:
        index = file.find(SAMPLE_DIR)
        subpath = file[index + len(SAMPLE_DIR) + 1:]
        plan: Plan = Plan()
        plan.category, plan.dataset, plan.sub_dataset = parse(subpath)
        readme_path = os.path.join(os.path.dirname(file), "README.md")
        is_windows = os.name == 'nt'
        if is_windows:
            with open(readme_path, encoding='utf-8') as stream:
                content = stream.read()
        else:
            with open(readme_path) as stream:  # 在 Linux 和 macOS 下不显式指定编码
                content = stream.read()
        plan.readme = content

        with open(file) as stream:
            try:
                recipe_model: Recipe = Recipe.parse_yaml(stream)
                plan.recipe = recipe_model
            except yaml.YAMLError as exc:
                print(exc)
        plans.append(plan)

    return plans

BUILDIN_SAMPLES = load_samples()

async def get_sample_categorys() -> list[str]:
    categorys: set = set()
    for plan in BUILDIN_SAMPLES:
        categorys.add(plan.category)

    return [item + " opensource dataset" for item in list(categorys)]


async def get_sample_dataset_category(category: Annotated[str, "str in 'refine' and 'reproduced'"]) -> list[dict]:
    return [{"dataset": plan.dataset, "sub_dataset": plan.sub_dataset, "readme": plan.readme} for plan in BUILDIN_SAMPLES if plan.category == category]

@dataclass
class SampleDetails:
    recipe: str
    tools: list[str]
    readme: str

def query_samples(dataset: str, sub_dataset: str = None, category: Annotated[str, "str in 'refine' and 'reproduced'"] = None) -> SampleDetails:
    plans: list[Plan] = list()
    for plan in BUILDIN_SAMPLES:
        if plan.dataset == dataset:
            if sub_dataset and plan.sub_dataset != sub_dataset:
                continue
            if category and plan.category != category:
                continue

            plans.append(plan)

    random_idx = random.randint(0, len(plans) - 1)
    sample = plans[random_idx]
    recipe = sample.recipe.yaml(include=["description", "process"])
    tools = [tool.name for tool in sample.tools_ordered]

    return SampleDetails(recipe, tools, sample.readme)
            

if __name__ == "__main__":
    # print(len(BUILDIN_SAMPLES))
    print(query_samples(dataset="pile"))


    