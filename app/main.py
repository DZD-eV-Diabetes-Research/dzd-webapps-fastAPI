import logging
import uvicorn
import requests

from config import DEFAULT
from Configs import getConfig
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase, AsyncGraphDatabase, basic_auth
import requests
from Configs import getConfig
from config import DEFAULT
import uvicorn
import logging

from fastAPIModels import (
    MeSHResult,
    GeneResult,
    Result,
    OrthologOverview,
    AnimalResult,
    Article,
    GWASInformation,
)
from sunBurstAnalyzer import SunburstData, SunburstDataContainer

config: DEFAULT = getConfig()

log = logging.getLogger(__name__)

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", status_code=200)
async def greeting() -> dict:
    return {"DZD": "Hello everyone"}


@app.get("/meshlist/", status_code=200, response_model=MeSHResult)
async def get_mesh_list() -> MeSHResult:
    """
    Returns the list of distinct MeSH-descriptors in the Neo4j database
    """

    query = """
    MATCH (n:MeshDescriptor)
    RETURN COLLECT(DISTINCT(n.text)) AS MeSHList
    """

    url = config.API_ORIGIN["url"]
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_PUBLIC_PROD["user"], config.NEO4J_PUBLIC_PROD["password"]
        ),
    )

    async def work(tx):
        result = await tx.run(query)
        return await result.single()

    async with driver.session() as session:
        result = await session.read_transaction(work)
        mesh_list = result["MeSHList"]

        return MeSHResult(MeSHList=mesh_list)


@app.get("/articlesbygenelist/", status_code=200, response_model=List[GeneResult])
async def articel_by_genes(
    mqt: str = Query(default="and_mesh"),
    g: list[str] = Query(default=[""]),
    b: list[str] = Query(default=["ThisIsAutofill"]),
    m: list[str] = Query(default=["ThisIsAutofill"]),
) -> List[GeneResult]:
    """Endpoint to generate a list of articles that mention the entered gene

    Args:
        mqt (str, optional): _description_. Defaults to Query(default="and_mesh").
        g (list[str], optional): _description_. Defaults to Query(default=[""]).
        b (list[str], optional): _description_. Defaults to Query(default=["ThisIsAutofill"]).
        m (list[str], optional): _description_. Defaults to Query(default=["ThisIsAutofill"]).

    Returns:
        dict: see response_model
    """

    first_part = """
    UNWIND $gene_symbols as x
        MATCH (g:Gene {symbol:x})
        -[:MENTIONED_IN]->(p:PubMedArticle)
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

    final_part = "RETURN DISTINCT p.ArticleTitle AS ArticleTitle, g.symbol AS Symbol, p.PMID AS PubMedArticle"

    query = first_part + meshQuery + blockQuery + final_part

    ###
    # py2neo connection works but blocks multiple Queries due to the fact that fast api with async thinks the query is not an I/O process
    # but a cpu process. Multiple queries work can excecute parallel if we remove async from the from the "async def articel_by_genes"
    # because then fastapi will open multiple threads.
    ###

    # graph = Graph(
    #     "bolt://neo4j02.connect.dzd-ev.de:9686",
    #     auth=("public", "secret"),
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
    # driver = GraphDatabase.driver(uri, auth=("public", "secret"))

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

    url = config.API_ORIGIN["url"]
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


###
# Sunburst
###


@app.get("/sunburst/")
async def sunburst(searchType: str, firstName: str, lastName: str) -> object:
    url = config.API_ORIGIN["url"]
    driver = AsyncGraphDatabase.driver(
        url,
        auth=basic_auth(
            config.NEO4J_ADMIN_QA["user"], config.NEO4J_ADMIN_QA["password"]
        ),
    )

    # test = f"""
    # MATCH (a:Author {{LastName:"{lastName}", ForeName:"{firstName}"}})<-[:CONTRIBUTION_HAS_AUTHOR]-(c:Contribution)<-[:PUBMEDARTICLE_HAS_CONTRIBUTION]-(pa:PubMedArticle)-[:PUBMEDARTICLE_HAS_JOURNALISSUE]->(ji:JournalIssue)-[:JOURNALISSUE_HAS_DATE]->(d:Date)
    # WITH a,ji,d,pa
    # MATCH (ji)-[:JOURNALISSUE_HAS_JOURNAL]->(j:Journal)
    # RETURN a.ForeName + " " + a.LastName AS Name, pa.ArticleTitle, COLLECT(DISTINCT pa.PMID) , d.Year AS Year, j.ISOAbbreviation AS Title
    # ORDER BY Year
    # """

    if searchType == "mesh":
        query = f"""MATCH (a:Author {{LastName:"{lastName}", ForeName:"{firstName}"}})<-[:CONTRIBUTION_HAS_AUTHOR]-(c:Contribution)<-[:PUBMEDARTICLE_HAS_CONTRIBUTION]-(pa:PubMedArticle)
        WITH COLLECT(DISTINCT pa.PMID) AS pmids
        UNWIND pmids as pmid
        MATCH (pa: PubMedArticle {{PMID:pmid}})-[r1:PUBMEDARTICLE_HAS_JOURNALISSUE]->(ji:JournalIssue)-[:JOURNALISSUE_HAS_DATE]->(d:Date)
        WITH pa, d
        MATCH (pa)-[:PUBMEDARTICLE_HAS_MESHHEADINGLIST]->(mhl:MeshHeadingList)-[:MESHHEADINGLIST_HAS_MESHHEADING]->(mh:MeshHeading)-[:MESHHEADING_HAS_MESHDESCRIPTOR]->(md:MeshDescriptor)
        RETURN d.Year AS Year, SIZE(COLLECT(DISTINCT pa.PMID)) AS ArticlePerYear, COLLECT(md.text) AS Items"""

    elif searchType == "journal":
        query = f"""MATCH (a:Author {{LastName:"{lastName}", ForeName:"{firstName}"}})<-[:CONTRIBUTION_HAS_AUTHOR]-(c:Contribution)<-[:PUBMEDARTICLE_HAS_CONTRIBUTION]-(pa:PubMedArticle)
        WITH COLLECT(DISTINCT pa.PMID) AS pmids
        UNWIND pmids as pmid
        MATCH (pa: PubMedArticle {{PMID:pmid}})-[r1:PUBMEDARTICLE_HAS_JOURNALISSUE]->(ji:JournalIssue)-[:JOURNALISSUE_HAS_DATE]->(d:Date)
        WITH pa, d, ji
        MATCH (ji)-[:JOURNALISSUE_HAS_JOURNAL]->(j:Journal)
        RETURN d.Year AS Year, SIZE(COLLECT(DISTINCT pa.PMID)) AS ArticlePerYear, COLLECT(j.ISOAbbreviation) AS Items"""

    async def work(tx):
        result = await tx.run(query)
        return await result.data()

    async with driver.session() as session:
        result = await session.execute_read(work)

        sunburstData = SunburstData()
        sunburstData.setName(f"{firstName} {lastName}")
        sunburstData.from_neo4j_data(result)
        sunburstData = [sunburstData]
        sunburstData = SunburstDataContainer(
            firstName=firstName,
            lastName=lastName,
            chartData=sunburstData,
            chartLayout={
                "colorscale": "Viridis",
                "height": None,
                "width": None,
            },
        )

        return sunburstData


###
# Maus-Klinik
###


@app.get(
    "/mouseclinic/getOverviewOrthologues/",
    status_code=200,
    response_model=List[OrthologOverview],
)
async def getOrthologues(g: list[str] = Query(default=[""])) -> List[OrthologOverview]:
    """Returns number of different orthologues of different species of the gene of interest

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see respone_model
    """

    url = config.API_ORIGIN["url"]
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
    WHEN g2.taxid = "7955" THEN "Zebrafish"
    WHEN g2.taxid = "7227" THEN "FruitFly"
    WHEN g2.taxid = "6239" THEN "C_elegans"
    WHEN g2.taxid = "10116" THEN "Rat"
    WHEN g2.taxid = "9823" THEN "Pig"
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


@app.get("/mouseclinic/getHuman/", status_code=200, response_model=List[AnimalResult])
async def getHuman_by_genes(g: list[str] = Query(default=[""])) -> List[AnimalResult]:
    """Returns list of articles, pubmedID, link, title, year for the "human" organism

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    url = config.API_ORIGIN["url"]
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
    WITH HumanGene,p
    MATCH (pt:PublicationType)--(p:PubMedArticle)-[:PUBMEDARTICLE_HAS_DATE]->(d:Date)
    RETURN DISTINCT "PMID" AS source, "Human" AS organism, p.PMID as pmId, pt.text AS PublicationType, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link, d.Year AS Year order by Year DESC
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


@app.get("/mouseclinic/getMouse/", status_code=200, response_model=List[AnimalResult])
async def getMouse_by_genes(g: list[str] = Query(default=[""])) -> List[AnimalResult]:
    """Returns list of articles, pubmedID, link, title, year for the "mouse" organism

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    url = config.API_ORIGIN["url"]
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
    WITH HumanGene,p
    MATCH (pt:PublicationType)--(p:PubMedArticle)-[:PUBMEDARTICLE_HAS_DATE]->(d:Date)
    RETURN DISTINCT "PMID" AS source, "Mouse" AS organism, p.PMID as pmId, pt.text AS PublicationType, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link, d.Year AS Year order by Year DESC
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


@app.get(
    "/mouseclinic/getZebrafish/", status_code=200, response_model=List[AnimalResult]
)
async def getFish_by_genes(g: list[str] = Query(default=[""])) -> List[AnimalResult]:
    """Returns list of articles, pubmedID, link, title, year for the "zebrafish" organism

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    url = config.API_ORIGIN["url"]
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
    WITH HumanGene,p
    MATCH (pt:PublicationType)--(p:PubMedArticle)-[:PUBMEDARTICLE_HAS_DATE]->(d:Date)
    RETURN DISTINCT "PMID" AS source, "Zebrafish" AS organism, p.PMID as pmId, pt.text AS PublicationType, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link, d.Year AS Year order by Year DESC
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


@app.get("/mouseclinic/getRat/", status_code=200, response_model=List[AnimalResult])
async def getRat_by_genes(g: list[str] = Query(default=[""])) -> List[AnimalResult]:
    """Returns list of articles, pubmedID, link, title, year for the "rat" organism

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    url = config.API_ORIGIN["url"]
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
    WITH HumanGene,p
    MATCH (pt:PublicationType)--(p:PubMedArticle)-[:PUBMEDARTICLE_HAS_DATE]->(d:Date)
    RETURN DISTINCT "PMID" AS source, "Rat" AS organism, p.PMID as pmId, pt.text AS PublicationType, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link, d.Year AS Year order by Year DESC
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


@app.get("/mouseclinic/getPig/", status_code=200, response_model=List[AnimalResult])
async def getPig_by_genes(g: list[str] = Query(default=[""])) -> List[AnimalResult]:
    """Returns list of articles, pubmedID, link, title, year for the "pig" organism

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    url = config.API_ORIGIN["url"]
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
    MATCH (HumanGene)-[r:ORTHOLOG]->(PigGene:Gene {taxid: "9823"})-[:MENTIONED_IN]-(p:PubMedArticle)
    WITH HumanGene,p
    MATCH (pt:PublicationType)--(p:PubMedArticle)-[:PUBMEDARTICLE_HAS_DATE]->(d:Date)
    RETURN DISTINCT "PMID" AS source, "Pig" AS organism, p.PMID as pmId, pt.text AS PublicationType, p.ArticleTitle AS title, "https://pubmed.ncbi.nlm.nih.gov/" + p.PMID AS link, d.Year AS Year order by Year DESC
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


@app.get("/mouseclinic/getC_elegans/", status_code=200, response_model=List[Result])
async def getWorm_by_genes(g: list[str] = Query(default=[""])) -> List[Result]:
    """Returns list of articles, pubmedID, link, title, year for the "c_elegans" organism

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    url = config.API_ORIGIN["url"]
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


@app.get("/mouseclinic/getFruitFly/", status_code=200, response_model=List[Result])
async def getFly_by_genes(g: list[str] = Query(default=[""])) -> List[Result]:
    """Returns list of articles, pubmedID, link, title, year for the "fruit fly" organism

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    url = config.API_ORIGIN["url"]
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


@app.get(
    "/mouseclinic/getPudMedID2Title/", status_code=200, response_model=List[Article]
)
async def getPudMedID2Title(g: list[str] = Query(default=[""])) -> List[Article]:
    """Returns a list of articles corresponding to the entered pubmedIDs

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    url = config.API_ORIGIN["url"]
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


@app.get(
    "/mouseclinic/getGWASinformation/",
    status_code=200,
    response_model=List[GWASInformation],
)
async def getGWAS_by_genes(g: list[str] = Query(default=[""])) -> List[GWASInformation]:
    """Returns the genesymbol, snp, trait, link of the entered gene

    Args:
        g (list[str], optional): _description_. Defaults to Query(default=[""]).

    Returns:
        dict: see response model
    """

    query = """
    UNWIND $gene_symbols as x
    MATCH (g:Gene) WHERE toUpper(g.Symbol) = toUpper(x)
    WITH g
    MATCH (g)-[:MAPS*0..2]-(gs3:Gene)
    -[:SNP_HAS_GENE]-(n:SNP)
    -[:SNP_HAS_ASSOCIATION]-(a:Association)
    -[:ASSOCIATED_WITH_TRAIT]-(t:Trait)
    RETURN DISTINCT g.Symbol AS Gene, n.snp_id AS SNP, t.name AS Trait, t.efo_trait_uri AS Link
    """

    url = config.API_ORIGIN["url"]
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


@app.post("/melodi/{melodi_presto_api_request:path}", status_code=200)
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
