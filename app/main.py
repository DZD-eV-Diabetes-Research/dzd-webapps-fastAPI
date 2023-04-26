from lib2to3.pytree import Base
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from neo4j import GraphDatabase, AsyncGraphDatabase, basic_auth
import requests
from Configs import getConfig
from config import DEFAULT
import uvicorn
from pydantic import BaseModel
import logging

config: DEFAULT = getConfig()


log = logging.getLogger(__name__)


class QueryResult(BaseModel):
    source: str
    organism: str
    pmId: str
    title: str
    link: str


class Result(BaseModel):
    source: str
    organism: str
    pmId: str
    title: str
    link: str


class ClientQuery(BaseModel):
    query: str
    query_result: QueryResult


app = FastAPI()

origins = ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def greeting():
    return {"DZD": "Hello everyone"}


@app.get("/meshlist/")
async def get_mesh_list():

    query = """
    MATCH (n:MeshDescriptor)
    RETURN COLLECT(DISTINCT(n.text)) AS MeSHList
    """

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_PUBLIC_PROD["user"], config.NEO4J_PUBLIC_PROD["password"]
        ),
    )

    async def work(tx):
        result = await tx.run(query)
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        return result


@app.get("/articlebygenelist/")
async def articel_by_genes(g: list[str] = Query(default=[""])):

    query = """
    UNWIND $gene_symbols as x
        MATCH (g:Gene {sid:x})
        -[:REPLACED_BY*0..1]-(gs2:Gene)
        -[:MAPS*0..2]-(gs3:Gene)
        -[:SYNONYM*0..1]-(gs4:Gene)
        <-[:MENTIONS]-(at:AbstractText)
        <-[:ABSTRACT_HAS_ABSTRACTTEXT]-(a:Abstract)
        <-[:PUBMEDARTICLE_HAS_ABSTRACT]-(p:PubMedArticle)
        -[:PUBMEDARTICLE_HAS_MESHHEADINGLIST]->
        (mhl:MeshHeadingList)-[*1..2]->
        (md:MeshDescriptor)
    RETURN DISTINCT g.sid AS Sid, p.ArticleTitle AS ArticleTitle
    """

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_PUBLIC_PROD["user"], config.NEO4J_PUBLIC_PROD["password"]
        ),
    )

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)
        return result


@app.get("/genesbygenelist/")
async def articel_by_genes(
    mqt: str = Query(default="and_mesh"),
    g: list[str] = Query(default=[""]),
    b: list[str] = Query(default=["ThisIsAutofill"]),
    m: list[str] = Query(default=["ThisIsAutofill"]),
):

    first_part = """
    UNWIND $gene_symbols as x
        MATCH (g:Gene {sid:x})
        -[:REPLACED_BY*0..1]-(gs2:Gene)
        -[:MAPS*0..2]-(gs3:Gene)
        -[:SYNONYM*0..1]-(gs4:Gene)
        <-[:MENTIONS]-(at:AbstractText)
        <-[:ABSTRACT_HAS_ABSTRACTTEXT]-(a:Abstract)
        <-[:PUBMEDARTICLE_HAS_ABSTRACT]-(p:PubMedArticle)
        -[:PUBMEDARTICLE_HAS_MESHHEADINGLIST]->
        (mhl:MeshHeadingList)-[*1..2]->
        (md:MeshDescriptor)
    """
    meshQuery = ""
    blockQuery = ""

    if m[0] != "ThisIsAutofill" and mqt == "and_mesh":
        for i, meshTerm in enumerate(m):
            if i == 0:
                meshQuery += f"WHERE toLower(md.text) contains toLower('{meshTerm}') "
            else:
                meshQuery += f" AND toLower(md.text) contains toLower('{meshTerm}') "

    if m[0] != "ThisIsAutofill" and mqt == "or_mesh":
        for i, meshTerm in enumerate(m):
            if i == 0:
                meshQuery += f"WHERE toLower(md.text) contains toLower('{meshTerm}') "
            else:
                meshQuery += f" OR toLower(md.text) contains toLower('{meshTerm}') "

    if b[0] != "ThisIsAutofill":
        for i, blockTerm in enumerate(b):
            if i == 0 and m[0] == "ThisIsAutofill":
                blockQuery += (
                    f"WHERE not toLower(md.text) contains toLower('{blockTerm}') "
                )
            else:
                blockQuery += (
                    f" AND not toLower(md.text) contains toLower('{blockTerm}') "
                )

    final_part = "RETURN DISTINCT p.ArticleTitle AS ArticleTitle, g.sid AS Sid, p.PMID AS PubMedArticle"

    query = first_part + meshQuery + blockQuery + final_part

    ###
    # py2neo connection works but blocks multiple Queries due to the fact that fast api with async thinks the query is not an I/O process
    # but a cpu process. Multiple queries work can excecute parallel if we remove async from the from the "async def articel_by_genes"
    # because then fastapi will open multiple threads.
    ###

    # graph = Graph(
    #     "bolt://neo4j02.connect.dzd-ev.de:9686",
    #     auth=("public", "Ah3xxv2pcbNCZKM9"),
    # )

    # res = graph.run(query, meshTerm=m, blockTerm=b, gene_symbols=g).data()
    # return res

    #############################

    ###
    #
    # official neo4j driver
    #
    ###

    # uri = "bolt://neo4j02.connect.dzd-ev.de:9686"
    # driver = GraphDatabase.driver(uri, auth=("public", "Ah3xxv2pcbNCZKM9"))

    # def work(tx):
    #     result = tx.run(
    #         query, {"gene_symbols": g, "blockTerm": b, "meshTerm": m}
    #     ).data()
    #     return result

    # db = driver.session()
    # result = db.read_transaction(work)
    # driver.close()

    # return result

    ################################

    ###
    #
    #   Async neo4j
    #
    ###

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_PUBLIC_PROD["user"], config.NEO4J_PUBLIC_PROD["password"]
        ),
    )

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g, "blockTerm": b, "meshTerm": m})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)
        return result


@app.get("/proteinbygenelist/")
async def articel_by_genes(g: list[str] = Query(default=[""])):
    query = """
    UNWIND $gene_symbols as x
        MATCH (g:Gene {sid:x})
        -[:REPLACED_BY*0..1]-(gs2:Gene)
        -[:MAPS*0..2]-(gs3:Gene)
        -[:SYNONYM*0..1]-(gs4:Gene)
        <-[:MENTIONS]-(at:AbstractText)
        <-[:ABSTRACT_HAS_ABSTRACTTEXT]-(a:Abstract)
        <-[:PUBMEDARTICLE_HAS_ABSTRACT]-(p:PubMedArticle)
        -[:PUBMEDARTICLE_HAS_MESHHEADINGLIST]->
        (mhl:MeshHeadingList)-[*1..2]->
        (md:MeshDescriptor)
    RETURN DISTINCT g.sid AS Sid, p.ArticleTitle AS ArticleTitle
    """

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_PUBLIC_PROD["user"], config.NEO4J_PUBLIC_PROD["password"]
        ),
    )

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)
        return result


###
# Maus-Klinik
###


@app.get("/mouseclinic/getOverviewOrthologues/")
async def getOrthologues(g: list[str] = Query(default=[""])):

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    query = """
    //Query shows Overview of orthologue genes

    UNWIND $gene_symbols as x
    MATCH path=(g:Gene {symbol:x})-[r:ORTHOLOG*0..2]-(g2)
    RETURN DISTINCT
    CASE 
    WHEN g2.taxid = "10090" THEN "Mouse"
    WHEN g2.taxid = "9606" THEN "Human"
    WHEN g2.taxid = "7955" THEN "Fish"
    WHEN g2.taxid = "7227" THEN "Fly"
    WHEN g2.taxid = "6239" THEN "Worm"
    WHEN g2.taxid = "10116" THEN "Rat"
    END AS Species, g2.symbol AS Symbol, g2.Full_name_from_nomenclature_authority AS Name, g2.sid AS SID, g2.source AS Source
    """

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        # test_list: List[Result] = []

        # for element in result:
        #     test_list.append(Result(**element))

        # return test_list
        return result


@app.get("/mouseclinic/getHuman/", response_model=list[Result])
async def getHuman_by_genes(g: list[str] = Query(default=[""])):

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    query = """
    UNWIND $gene_symbols as x
    MATCH (g:Gene) WHERE toUpper(g.symbol) = toUpper(x) AND g.taxid = "9606"
    WITH g AS HumanGene
    MATCH (HumanGene)-[:MENTIONED_IN]-(p:PubMedArticle)
    RETURN DISTINCT "PMID" AS source, "Human" AS organism,   p.PMID as pmId, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link
    """

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        test_list: List[Result] = []

        for element in result:
            test_list.append(Result(**element))

        return test_list


@app.get("/mouseclinic/getMouse/", response_model=list[Result])
async def getMouse_by_genes(g: list[str] = Query(default=[""])):

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    query = """
    UNWIND $gene_symbols as x
    MATCH (g:Gene) WHERE toUpper(g.symbol) = toUpper(x) AND g.taxid = "9606"
    WITH g AS HumanGene
    MATCH (HumanGene)-[r:ORTHOLOG]->(MouseGene:Gene {taxid: "10090"})-[:MENTIONED_IN]-(p:PubMedArticle)
    RETURN DISTINCT "PMID" AS source, "Mouse" AS organism, p.PMID as pmId, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link
    """

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        test_list: List[Result] = []

        for element in result:
            test_list.append(Result(**element))

        return test_list


@app.get("/mouseclinic/getZebrafish/", response_model=list[Result])
async def getFish_by_genes(g: list[str] = Query(default=[""])):

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    query = """
    UNWIND $gene_symbols as x
    MATCH (g:Gene) WHERE toUpper(g.symbol) = toUpper(x) AND g.taxid = "9606"
    WITH g AS HumanGene
    MATCH (HumanGene)-[r:ORTHOLOG]->(FishGene:Gene {taxid: "7955"})-[:MENTIONED_IN]-(p:PubMedArticle)
    RETURN DISTINCT "PMID" AS source, "Zebrafish" AS organism, p.PMID as pmId, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link
    """

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        test_list: List[Result] = []

        for element in result:
            test_list.append(Result(**element))

        return test_list


@app.get("/mouseclinic/getRat/", response_model=list[Result])
async def getRat_by_genes(g: list[str] = Query(default=[""])):

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    query = """
    UNWIND $gene_symbols as x
    MATCH (g:Gene) WHERE toUpper(g.symbol) = toUpper(x) AND g.taxid = "9606"
    WITH g AS HumanGene
    MATCH (HumanGene)-[r:ORTHOLOG]->(RatGene:Gene {taxid: "10116"})-[:MENTIONED_IN]-(p:PubMedArticle)
    RETURN DISTINCT "PMID" AS source, "Rat" AS organism, p.PMID as pmId, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link
    """

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        test_list: List[Result] = []

        for element in result:
            test_list.append(Result(**element))

        return test_list


@app.get("/mouseclinic/getC_elegans/", response_model=list[Result])
async def getWorm_by_genes(g: list[str] = Query(default=[""])):

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    query = """
    UNWIND $gene_symbols as x
    MATCH (g:Gene) WHERE toUpper(g.symbol) = toUpper(x) AND g.taxid = "9606"
    WITH g AS HumanGene
    MATCH (HumanGene)-[r:ORTHOLOG]->(WormGene:Gene {taxid: "6239"})-[:MENTIONED_IN]-(p:PubMedArticle)
    RETURN DISTINCT "PMID" AS source, "C.Elegans" AS organism, p.PMID as pmId, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link
    """

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        test_list: List[Result] = []

        for element in result:
            test_list.append(Result(**element))

        return test_list


@app.get("/mouseclinic/getFruitFly/", response_model=list[Result])
async def getFly_by_genes(g: list[str] = Query(default=[""])):

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    query = """
    UNWIND $gene_symbols as x
    MATCH (g:Gene) WHERE toUpper(g.symbol) = toUpper(x) AND g.taxid = "9606"
    WITH g AS HumanGene
    MATCH (HumanGene)-[r:ORTHOLOG]->(FlyGene:Gene {taxid: "7227"})-[:MENTIONED_IN]-(p:PubMedArticle)
    RETURN DISTINCT "PMID" AS source, "Fruit Fly" AS organism, p.PMID as pmId, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link
    """

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        test_list: List[Result] = []

        for element in result:
            test_list.append(Result(**element))

        return test_list


@app.get("/mouseclinic/getPudMedID2Title/")
async def getPudMedID2Title(g: list[str] = Query(default=[""])):

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    query = """
    //Query shows titels for PMIDs

    UNWIND $PM_IDs as x
    MATCH (p:PubMedArticle {PMID: x})
    RETURN p.PMID AS PMID, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link
    """

    async def work(tx):
        result = await tx.run(query, {"PM_IDs": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        # test_list: List[Result] = []

        # for element in result:
        #     test_list.append(Result(**element))

        # return test_list
        return result


@app.get("/mouseclinic/getGWASinformation/")
async def getGWAS_by_genes(g: list[str] = Query(default=[""])):
    query = """
    UNWIND $gene_symbols as x
        MATCH (t:Trait)-[ASSOCIATED_WITH_TRAIT]-
        (a:Association)-[SNP_HAS_ASSOCIATION]-
        (n:SNP)-[SNP_HAS_GENE]-
        (g:Gene {sid: x}) 
        RETURN DISTINCT g.sid, n.snp_id, t.name, t.efo_trait_uri
    """

    url = config.API_ORIGIN['url']
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_PUBLIC_PROD["user"], config.NEO4J_PUBLIC_PROD["password"]
        ),
    )

    async def work(tx):
        result = await tx.run(query, {"gene_symbols": g})
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)
        return result


@app.post("/melodi/{melodi_presto_api_request:path}")
async def melodi_presto_proxy_endpoint(melodi_presto_api_request: str, payload: str):
    """Accepts a melodi presto api call. Prevents CORS errors in client side.
    see https://melodi-presto.mrcieu.ac.uk/docs/ for details on the API

    Args:
        melodi_presto_api_request (str): the API endpoint. e.g. `enrich/`
        payload (str): The post payload. e.g. `{"query": "PCSK9"}`

    Returns:
        _type_: _description_
    """
    # return melodi_presto_api_request, gene
    base_url: str = "https://melodi-presto.mrcieu.ac.uk/api/"
    api_call_url = base_url + melodi_presto_api_request

    # curl -X POST "https://melodi-presto.mrcieu.ac.uk/api/enrich/" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{  \"query\": \"PCSK9\"}"
    res = requests.post(
        api_call_url,
        data=payload,
        headers={"accept": "application/json", "Content-Type": "application/json"},
    )
    res.raise_for_status()
    return res.content


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, **config.UVICORN_WEBSERVER_PARAMS)
