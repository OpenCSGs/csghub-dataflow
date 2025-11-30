from data_server.logic.models import Recipe
import yaml
import os
import glob

if __name__ == "__main__":
    # print(len(BUILDIN_TEMPLATES))
    # folder_path = '/Users/lipeng/workspaces/git-devops/data-flow/configs/templates'
    # file_list = glob.glob(os.path.join(folder_path, '*.yaml'))

    # for file in file_list:
    #     print("==================")
    #     print(file)
    #     with open(file) as stream:
    #         try:
    #             base_model = Recipe.parse_yaml(stream)
    #             print(base_model.model_dump())
    #             print(base_model.yaml())
    #         except yaml.YAMLError as exc:
    #             print(exc)
    # 
    # with open("/Users/lipeng/workspaces/git-devops/data-flow/configs/templates/pile-pubmed-central-refine.yaml") as stream:
    with open("configs/templates/process.yaml") as stream:
        try:
            base_model = Recipe.parse_yaml(stream)
            print(base_model.process)
            print("=======")
            print(base_model.yaml())
            file_path = "file.yaml"  # Replace with the desired file path

            with open(file_path, "w") as file:
                file.write(base_model.yaml())
            # print(base_model.yaml())
        except yaml.YAMLError as exc:
            print(exc)
