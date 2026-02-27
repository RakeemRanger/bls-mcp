import requests
import json
import prettytable
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from utils.json_util import JsonUtility
from configs.CONSTANTS import (
    BLS_SERIES_RELATIVE_PATH,
    BLS_API_ENDPOINT
)


class BlsDataSeriesFetcher:
    """
    Fetches BLS series 
    """
    def __init__(self, ):
        self.series_file = Path(BLS_SERIES_RELATIVE_PATH).resolve()
        self.json_util = JsonUtility(str(self.series_file))
        self.loaded_json = self.json_util.load()
    
    def fetch_all_series(self,
                         series_ids: list = [],
                         start_year: str = '2011',
                         ) -> None:
        self.series_list = []
        self.end_year = str(datetime.now().year)
        if len(series_ids) == 0:
            raise Exception('No BLS series to process')
        for id in series_ids:
            self.series_list.append(id)
        headers = {'Content-type': 'application/json'}
        data = json.dumps({"seriesid": self.series_list,"startyear":f"{start_year}", "endyear":f"{self.end_year}"})
        try:
            p = requests.post(BLS_API_ENDPOINT, data=data, headers=headers)
            json_data = json.loads(p.text)
        except Exception as e:
            raise Exception(f'Issue requesting BLS Data: {e}')
        for series in json_data['Results']['series']:
            series = series
        return series