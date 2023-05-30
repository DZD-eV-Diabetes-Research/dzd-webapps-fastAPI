# DZD-FastAPI

FastAPI for the DZD-Webapps (BillyGene [[git](https://github.com/DZD-eV-Diabetes-Research/dzd-webapps-billy_gene)], MiceAndMan [[git](https://github.com/DZD-eV-Diabetes-Research/dzd-micemen)]) 

**Maintainer**: Justus Täger - taeger@dzd-ev.de

**Licence**: MIT

**source code**: https://github.com/DZD-eV-Diabetes-Research/dzd-webapps-fastAPI


---

**Content**:

- DZD-FastApi
- Download
- What is the DZD-FastAPI
  - Endpoints
  - How to use 

---

## **Download**

`git clone https://github.com/DZD-eV-Diabetes-Research/dzd-webapps-fastAPI`

## **What is the DZD-FastAPI**

The DZD-FastAPI is a REST(**R**epresentational **S**tate **T**ransfer)ful-API which allows two software applications (for now our DZD-Apps and our Neo4jDB) to communicate with each other over the internet. It does so by using the typical HTTP methods (such as GET, POST, PUT, DELETE). The API can be divided into three sections: General, BillyGene and MiceAndMen. Each one of the DZD-Webapps has their own list of endpoints. If you are want to communicate in any way with our DZD-Graph and none of the endpoints are to your satisfaction feel free to contact us with your suggestions. These are our current endpoints:

### **Endpoints**

**GENERAL**
- GET - **"/"**
  - params: NONE 
  - return: Greeting
  - purpose: Because we are friendly
  
**BillyGene**
- GET - "/**meshlist**"
  - params: NONE
  - return: List of MeSH-Terms (str) 
  - purpose: Required for the MeSH-Term suggestion for [BillyGene](LinkkommtNoch.de)
- GET - "/**genesbygenelist**/"
  -  params:
     -  required:
        -  g: List(str) of Gene-symbols 
        -  mqt: "and_mesh" (default) or "or_mesh"
     -  optional:
        -  b: List(str) of MeSHTerms that should be blocked
        -  m: List(str) of MeSHTerms that have to be included
  - return: A list of pubmed-articles with the title of the article the gene Symbol and the PubmedID 

**MiceAndMen**
- GET - "/mouseclinic/**getOverviewOrthologues**/"
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of the number of ortholog genes in different species (Mouse, Human, Zebrafish, FruitFly, C_elegans, Rat, Pig)
- GET - "/mouseclinic/**getHuman**/"
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of: "Human" as organims, pubmedID, publication type, article title, link to the article, year of publication of the mentioned gene
- GET - "/mouseclinic/**getMouse**/"
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of: "Mouse" as organims, pubmedID, publication type, article title, link to the article, year of publication of the mentioned gene
- GET - "/mouseclinic/**getZebrafish**/"
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of: "Zebrafish" as organims, pubmedID, publication type, article title, link to the article, year of publication of the mentioned gene
- GET - "/mouseclinic/**getRat**/"
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of: "Rat" as organims, pubmedID, publication type, article title, link to the article, year of publication of the mentioned gene
- GET - "/mouseclinic/**getPig**/"
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of: "Pig" as organims, pubmedID, publication type, article title, link to the article, year of publication of the mentioned gene
- GET - "/mouseclinic/**getC_elegans**/"
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of: "C_elegans" as organims, pubmedID, publication type, article title, link to the article, year of publication of the mentioned gene
- GET - "/mouseclinic/**getFruitFly**/"
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of: "FruitFly" as organims, pubmedID, publication type, article title, link to the article, year of publication of the mentioned gene
- GET - **"/mouseclinic/getPudMedID2Title/"**
  - params:
    - required:
      -  g: List(str) of PubMedIds
   - return: A list of PubmedIds, articletitle and the link to the article
- GET - **"/mouseclinic/getGWASinformation/"**
  - params:
    - required:
      -  g: List(str) of Gene-symbols
   - return: A list of the genesymbols the SNP-id, trait, and efo trait uri as a link
- POST - **"/melodi/{melodi_presto_api_request:path}"**
  - params:
    - required:
      - melodi_presto_api_request (str)
      - payload (str) e.g. `{"query": "PCSK9"}`
  - return: Melodi presto API call

### **How to use** 

When using this API you have 2 main ways an easy one and one a little bit more complicated. 

1. Use the FastAPI we host [here](linkKommtNoch.de).
   
2. Clone our repository and configure it to your liking. For that you need to 
- a) clone this repository 
- b) create an .env file
- c) add the following enviornment variables:
  - API_ORIGIN['url']
  - NEO4J_PUBLIC_PROD["user"]
  - NEO4J_PUBLIC_PROD["password"]
- d) run the main.py file

If you don't already have access to our graph feel free to contact us.
