from pydantic import BaseModel, Field
from typing import List, Dict, Literal
import uuid


class SunburstData(BaseModel):
    type_: Literal["sunburst"] = Field(by_alias=True, alias="type", default="sunburst")
    ids: List[str] = []
    labels: List[str] = []
    parents: List[str] = [""]
    values: List[int] = []
    # marker = {"colorscale": "Viridis"}
    name: str = Field(exclude=True, default="")
    help_counter_1 = Field(exclude=True, default=0)
    year_counter = Field(exclude=True, default=0)

    def setName(self, name):
        self.name = name
        self.ids.append(self.name)
        self.labels.append(self.name)

    def from_neo4j_data(self, data: List[Dict]):
        for item in data:
            self.help_counter_1 += 1
            self.parents.insert(1, self.name)
            self._parse_data_obj(item)

        self.values.insert(0, sum(self.values[0 : self.year_counter]))

    def _parse_data_obj(self, data: Dict):
        if data["Year"] not in self.ids:
            self.ids.insert(self.help_counter_1, data["Year"])
            self.labels.insert(self.help_counter_1, data["Year"])
        self.values.insert(self.year_counter, len(data["Items"]))
        self.year_counter += 1

        help_list2 = []
        value_list = []
        for title in data["Items"]:
            if title not in help_list2:
                help_list2.append(title)
                value_list.append(data["Items"].count(title))

        self.values.extend(value_list)

        help_list = []

        for title in data["Items"]:
            if title + "_" + data["Year"] not in self.ids:
                self.parents.append(data["Year"])
                self.ids.append(title + "_" + data["Year"])
            if title not in help_list:
                help_list.append(title)

        self.labels.extend(help_list)


class SunburstDataContainer(BaseModel):
    firstName: str
    lastName: str
    chartData: list[SunburstData]
    chartLayout: Dict
