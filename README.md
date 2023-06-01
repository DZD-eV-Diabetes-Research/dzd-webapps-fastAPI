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

see here https://api-micemen.dzd-ev.org/docs

### **How to use** 

When using this API you have 2 main ways an easy one and one a little bit more complicated. 

1. Use the FastAPI we host [here](https://api-micemen.dzd-ev.org).
   
2. Clone our repository and configure it to your liking. For that you need to 
- a) clone this repository 
- b) create an .env file
- c) add the following enviornment variables:
  - API_ORIGIN['url']
  - NEO4J_PUBLIC_PROD["user"]
  - NEO4J_PUBLIC_PROD["password"]
- d) run the main.py file

If you don't already have access to our graph feel free to contact us.
