import os
import json
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info
from loguru import logger

def task(key: str, url: str, prompt: str, model: str, base_url=None):
    """ 
    Task that execute the scraping:
        Arguments:
        - key (str): key of the model
        - url (str): url to scrape 
        - prompt (str): prompt
        - model (str): name of the model
        Return:
        - results_df["output"] (dict): result as a dictionary
        - results_df (pd.Dataframe()): result as padnas df
    """
    if base_url is not None:
        graph_config = {
            "llm": {
                "api_key": key,
                "model": model,
            },
        }
    else:
        graph_config = {
            "llm": {
                "api_key": key,
                "model": model,
                "openai_api_base": base_url,
            },
        }

    # ************************************************
    # Create the SmartScraperGraph instance and run it
    # ************************************************
    smart_scraper_graph = SmartScraperGraph(
        prompt=prompt,
        # also accepts a string with the already downloaded HTML code
        source=url,
        config=graph_config
    )

    result = smart_scraper_graph.run()
    graph_exec_info = smart_scraper_graph.get_execution_info()
    logger.info(prettify_exec_info(result))
    logger.info(prettify_exec_info(graph_exec_info))
    return result


def scrape_main(target_dir,
                url: str = 'https://top.baidu.com/board?tab=realtime',
                prompt: str = 'Give me all the news with their abstracts'):
    """
    Data scrape tool based on large language model for websites and native documents (XML, HTML, JSON, etc.).
    :param target_dir: path to store subset files(`jsonl` format)
    :param url: Enter the URL to scrape
    :param prompt: prompt to AI description of what data do you want scrape from url.
    """
    logger.info(f'target_dir: {target_dir}, url: {url}, prompt: {prompt}' )
    key = os.environ.get("AZURE_OPENAI_API_KEY", None)
    model = os.environ.get("AZURE_MODEL", None)
    graph_result = task(key, url, prompt, model)
    data = json.dumps(graph_result, indent=4, ensure_ascii=False)

    file_name = f'scraped_data.json'
    file_path = os.path.join(target_dir, file_name)
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(data.encode('utf-8'))

if __name__ == '__main__':
    target_dir = r"/Users/francis/go/src/git-devops/data-flow/outputs/scrapedata/"
    scrape_main(target_dir)
