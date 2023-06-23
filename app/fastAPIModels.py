from pydantic import BaseModel
from typing import List

class MeSHResult(BaseModel):
    MeSHList: List[str]

class GeneResult(BaseModel):
    ArticleTitle: str
    Symbol: str
    PubMedArticle: str

class OrthologOverview(BaseModel):
    Symbol: str
    Name: str
    SID: str
    Source: str

class AnimalResult(BaseModel):
    source: str
    organism: str
    pmId: str
    PublicationType: str
    title: str
    link: str
    Year: str

class Result(BaseModel):
    source: str
    organism: str
    pmId: str
    title: str
    link: str

class Article(BaseModel):
    PMID: str
    title: str
    link: str

class GWASInformation(BaseModel):
    Gene: str
    SNP: str
    Trait: str
    Link: str