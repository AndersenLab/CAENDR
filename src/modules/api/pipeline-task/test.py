import json
import random

from caendr.models.task import HeritabilityTask

from caendr.services.heritability_report import HERITABILITY_TASK_QUEUE_NAME, create_new_heritability_report
from caendr.utils.data import convert_data_table_to_tsv, get_object_hash, unique_id
from pipelines.heritability import start_heritability_pipeline
from routes.task import handle_task

def test():
    id = unique_id()
    username = "112478343793841308494" # rodolfovieiranu@gmail.com
    label = f"test_{id}"

    sample_data = """[["1", "CB4856", "Healthspan", "1", "12.9"], ["1", "CB4856", "Healthspan", "2", "10.2"], ["2", "CB4856", "Healthspan", "1", "10.5"], ["3", "CB4856", "Healthspan", "1", "9.2"], ["3", "CB4856", "Healthspan", "2", "11.2"], ["1", "CX11314", "Healthspan", "1", "12.1"], ["1", "CX11314", "Healthspan", "2", "12.5"], ["2", "CX11314", "Healthspan", "1", "12.5"], ["2", "CX11314", "Healthspan", "2", "10.5"], ["4", "CX11314", "Healthspan", "1", "13.1"], ["4", "CX11314", "Healthspan", "2", "11.6"], ["1", "DL238", "Healthspan", "1", "11.6"], ["2", "DL238", "Healthspan", "1", "10.6"], ["2", "DL238", "Healthspan", "2", "11"], ["3", "DL238", "Healthspan", "1", "11.3"], ["3", "DL238", "Healthspan", "2", "11"], ["1", "JT11398", "Healthspan", "1", "11.6"], ["1", "JT11398", "Healthspan", "2", "12.5"], ["2", "JT11398", "Healthspan", "1", "12.9"], ["2", "JT11398", "Healthspan", "2", "12.9"], ["4", "JT11398", "Healthspan", "1", "13.7"], ["4", "JT11398", "Healthspan", "2", "11.2"], ["1", "JU258", "Healthspan", "1", "12.2"], ["1", "JU258", "Healthspan", "2", "10.9"], ["2", "JU258", "Healthspan", "1", "11.9"], ["2", "JU258", "Healthspan", "2", "12.833"]]"""
    data = json.loads(sample_data)
    # make data unique to avoid input caching
    data[0][-1] = f"{ 11 + random.random()}"
    data_hash = get_object_hash(data, length=32)
    trait = data[0][2]

    columns = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]
    data_tsv = convert_data_table_to_tsv(data, columns)

    report = create_new_heritability_report(id, username, label, data_hash, trait, data_tsv)


def test_handle():
    # handle the task
    task_route = HERITABILITY_TASK_QUEUE_NAME
    payload = {
        'id': report.id,
        'kind': report.kind,
        'username': report.username,
        'container_name': report.container_name,
        'container_version': report.container_version,
        'container_repo': report.container_repo,
        'data_hash': data_hash
    }
    handle_task(payload, task_route)
    print(report)

if __name__ == "__main__":
    test()