import requests
from helper import load_dotenv
from pathlib import Path
import sqlite3
import json


def get_tasks( project_id ):
    config = load_dotenv()

    con = sqlite3.connect( config['LABEL_STUDIO_DB_PATH'] )

    c = con.cursor()
    c.execute(f'''
        SELECT t.id, t.project_id, t.total_annotations, isl.key FROM task t 
        JOIN io_storages_localfilesimportstoragelink isl
        ON t.id = isl.task_id
        WHERE t.project_id = { project_id }
    ''')
    tasks = c.fetchall()
    c.close()
    con.close()

    tasks = [
        {
            "id" : t[0],
            "project_id" : t[1],
            "total_annotations" : t[2],
            "data_path" : t[3]
        } for t in tasks
    ]

    return tasks

    # headers = {'Authorization': f'Token { token }'}
    # res = requests.get(
    #     f"http://localhost:8080/api/tasks?project={project_id}&limit=500",
    #     headers=headers
    # )

    # if res.status_code == 200:
    #     data = res.json()
    #     return data['tasks']

    # return None


def get_annotation_of_tasks( task_id, token ):
    headers = {'Authorization': f'Token { token }'}
    res = requests.get(
        f"http://localhost:8080/api/tasks/{task_id}/annotations/",
        headers=headers
    )

    if res.status_code == 200:
        return res.json()

    return []


def get_results_of_project( project_id, labels=[] ):
    """
        
    """
    config = load_dotenv()
    con = sqlite3.connect( config["LABEL_STUDIO_DB_PATH"] )
    # tasks by id
    tasks = get_tasks( project_id )

    tasks_by_id = {}
    
    for t in tasks:
        tasks_by_id[t['id']] = Path(t['data_path']).name

    # results
    c = con.cursor()
    c.execute(
        f"""
            SELECT task_id,result FROM task_completion
            WHERE result != "[]" AND task_id IN ({ ','.join([str(t['id']) for t in tasks]) })
        """
    )
    rows = c.fetchall()
    c.close()
    
    results = []

    for r in rows:
        task_id = int(r[0])
        res_task = json.loads(r[1])

        for res in res_task:
            res['task_id'] = task_id
            res['img_name'] = tasks_by_id[task_id]

            res['rectanglelabels'] = []
            if 'rectanglelabels' in res['value']:
                res['rectanglelabels'] = res['value']['rectanglelabels']

            # Moireposition auf Pixelwerte umbauen
            res['value'] = {
                'x' : round(res["original_width"] * (res['value']['x'] / 100)),
                'y' : round(res["original_height"] * (res['value']['y'] / 100)),
                'width' : round(res["original_width"] * (res['value']['width'] / 100)),
                'height' : round(res["original_height"] * (res['value']['height'] / 100))
            }

            results.append(res)

    if len(labels) == 0:
        return results
    
    results_out = []

    for r in results:
        for l in r['rectanglelabels']:
            if l in labels:
                results_out.append(r)
                break

    return results_out


def get_moires_of_project( project_id ):
    return get_results_of_project( project_id, labels=['moire'] )


def get_potential_moires_of_project( project_id ):
    return get_results_of_project( project_id, labels=['potential_moire'] )


def main():
    config = load_dotenv()

    annotations = get_moires_of_project(
        config['LABEL_STUDIO_PROJECT_ID']
    )

    # print( annotations )

if __name__ == '__main__':
    main()
