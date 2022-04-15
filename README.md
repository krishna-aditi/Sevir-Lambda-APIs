SEVIR Lambda functions for Summarization and Named-Entity Recognition
=================================

Report link (GoogleDoc): https://docs.google.com/document/d/1NyDmaHg2dv5cyK_g-cmX7KuiQ3NuAcH3muKhU8A9ddk/edit#heading=h.9fvmf7j8mnk5

CLAAT link: https://codelabs-preview.appspot.com/?file_id=1NyDmaHg2dv5cyK_g-cmX7KuiQ3NuAcH3muKhU8A9ddk#3

GCP host link for FastAPI - Swagger UI: https://sevir-nlp.ue.r.appspot.com

Data Studio Live Dashboard link: https://datastudio.google.com/embed/reporting/aba0d648-f51e-4817-87bc-c8dd5c8bf1af/page/iFzpC

Streamlit Cloud link: https://share.streamlit.io/krishna-aditi/sevir-lambda-apis/main/src/data/streamlit-app.py

==========================================================================

#### Nowcasting API using FastAPI web-framework for Federal Aviation Administration
Weather briefing is a vital part of any flight preparation. The National Weather Service (NWS), Federal Aviation Administration (FAA), Department of Defense and other aviation groups are responsible for coherent and accurate weather reporting. The combined efforts of thorough scientific study and modeling techniques are able to predict the weather patterns with increasing accuracy. These weather forecasts enable pilots to make informed decisions regarding weather and flight safety. 

#### Weather Radar Observations
The weather radar data is provided by the national network of WSR-88D (NEXRAD) radars. This data is the major source of weather sensing used for Nowcasting. The WSR-88D (NEXRAD), also known as the Doppler Radar has two operational modes- clear air and precipitation. The mode is changed based on the weather condition. 

The NEXRAD radar image is not real time and can be upto 5 minutes old. If these images are older than it can lead to fatal accidents, as they have in the past. They are displayed as mosaic images that have some latency in creation, and in some cases the age of the oldest NEXRAD data in the mosaic can exceed the age indication in the cockpit by 15 to 20 minutes. Even small-time differences between age-indicator and actual conditions can be important for safety of flight. 
A better approach to solving this problem is by using the SEVIR Nowcast model which predicts a sequence of 12 images corresponding to the next hour of weather, based on the previously captured 13 images sampled at 5 minute intervals. 

#### Objective
The goal of the project is to implement a REST API to execute the GAN model, which takes a sequence of 13 images as input and generates 12 images as output. The end users, who are a bunch of developers who want to integrate our API with their system, pass a JSON file as a blueprint with all required parameters through CURL, POSTMAN, or a Python-Client to execute the model. 

The API can be used as a foundation to be built upon and integrated with the existing Electronic Flight Display (EFD) or Multi-Function Display (MFD) that gives the pilot access to several data links to weather services that are made available through multiple resources. Along with Graphical NEXRAD data, city forecast data, graphical wind data, the system will also have near-term forecasted images for the requested area of interest and time.

#### Requirements
To test pretrained models and train API requires
```
Python 3.7
tensorflow 2.1.0
pandas
numpy
Streamlit
Python-jose
Passlib
Transformers 3.4
GCSFS
```
To visualize the outputs basemap library is required, which needs to following libraries
```
h5py 2.8.0
matplotlib 3.2.0
Streamlit
```
#### JSON Blueprint
```
{
 "lat":37.318363,
 "lon":-84.224203, 
 "radius":200,
 "time_utc":"2019-06-02 18:33:00",
 "model_type":"gan",
 "threshold_time_minutes":30,
 "closest_radius":true,
 "force_refresh":false
}
```
#### Fast API
FastAPI is a high-performance web-framework used for building APIs. The SEVIR API is built upon FastAPI.

Run the live server using Uvicorn:
```
$ uvicorn nowcast_main:app –reload
```
#### BigQuery User Logging for Nowcast API

![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/user_logging_bigquery.png)

#### HuggingFace BERT tutorial

##### Steps:
1. Create a Python Lambda function with the Serverless Framework
2. Add the BERT model to our function and create an inference pipeline
3. Create a custom docker image
4. Test our function locally with LRIE(Lambda Runtime Interface Emulator)
5. Deploy a custom docker image to ECR
6. Deploy AWS Lambda function with a custom docker image
7. Test our Serverless BERT API

![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/ecr_push.png)
Fig. BERT-Lambda docker image pushed to Amazon ECR

![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/bert-lambda-postman.png)
Fig. Testing BERT API on Postman

#### Docker
A Docker image is a file used to execute code in a Docker container. Docker images act as a set of instructions to build a Docker container, like a template. Docker images also act as the starting point when using Docker. An image is comparable to a snapshot in virtual machine (VM) environments. We created local images for the BERT tutorial, as well as for the Summarization and NER APIs.

##### Steps:
1. Create a requirements.txt file with all the dependencies you want to install in the docker
```
https://download.pytorch.org/whl/cpu/torch-1.5.0%2Bcpu-cp38-cp38-linux_x86_64.whl
transformers==3.4.0
geopy==2.2.0
pandas==1.4.2
```
2. Create a dockerfile in the same directory
```
FROM public.ecr.aws/lambda/python:3.8

# Copy function code and models into our /var/task
COPY ./ ${LAMBDA_TASK_ROOT}/

# install our dependencies
RUN python3 -m pip install -r requirements.txt --target ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "handler.handler" ]
```
3. Add a .dockerignore files to exclude files from your docker container image
```
README.md
*.pyc
*.pyo
*.pyd
__pycache__
.pytest_cache
serverless.yaml
get_model.py
```
4. Build the customer docker image
```
docker build -t sevir-summary-test .
```
5. AWS also released the Lambda Runtime Interface Emulator that enables us to perform local testing of the container image and check that it will run when deployed to Lambda. The docker can be started by running the following command
```
docker run -p 8080:8080 sevir-summary-test
```
6. In a separate terminal, locally invoke the function using CURL
```
curl --request POST --url http://localhost:8080/2015-03-31/functions/function/invocations --header 'Content-Type:application/json'  --data "{ \"lat\": 37.318363, \"lon\" : -84.224203, \"radius\" : 200, \"time_utc\" : \"2019-06-02 18:33:00\", \"closest_radius\" : true}"
```
![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/docker.png)
Fig. Docker Desktop with docker images for BERT-lambda tutorial and Summarization

#### Deploy the Summarization and NER docker images to ECR

##### What is ECR?
Amazon Elastic Container Registry (Amazon ECR) is an AWS managed container image registry service that is secure, scalable, and reliable. Amazon ECR supports private repositories with resource-based permissions using AWS IAM.

##### Steps:
1. Create an ECR repository with the name of your choice
```
aws ecr create-repository --repository-name sevir-summary-test > NUL
```

2. Set environment variables to configure the AWS CLI to login to ECR
```
aws_region=us-east-1
aws_account_id=<aws_account_id>
aws ecr get-login-password \
    --region $aws_region \
| docker login \
    --username AWS \
    --password-stdin $aws_account_id.dkr.ecr.$aws_region.amazonaws.com
```
3. Tag the previously created docker image in an ECR format
```
docker tag sevir-summary-test $aws_account_id.dkr.ecr.$aws_region.amazonaws.com/sevir-summary-test
```
4. Verify if the tagging worked on Docker Desktop
5. Push image to ECR Registry
```
docker push $aws_account_id.dkr.ecr.$aws_region.amazonaws.com/sevir-summary
```
![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/local_docker_test.png)
Fig. Testing summarization docker locally

#### Deploying AWS Lambda function with docker image
1. Create a serverless.yaml file with the following configuration
```
service: serverless-sevir-docker

provider:
  name: aws # provider
  region: us-east-1 # aws region
  memorySize: 5120 # optional, in MB, default is 1024
  timeout: 30 # optional, in seconds, default is 6

functions:
  summarize:
    image: <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/sevir-summary:latest #ecr url
    events:
      - http:
          path: summary# http path
          method: post # http method
```

2. Deploy the function using the following command
```
serverless deploy
```
![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/ecr_push.png)
Fig. Deploying the lambda function

#### Streamlit
Streamlit is an open-source python framework for building web apps for Machine Learning and Data Science. We can instantly develop web apps and deploy them easily using Streamlit. It allows you to write an app the same way you write a python code. It pulls data using FastAPI. 

You could also run it on your local system using the following command.
```
$ streamlit run streamlit-app.py
```
![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/streamlit_login.png)
Fig. User authentication on Streamlit

![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/streamlit_summary_api.png)
Fig. Event and Episode summarization

![image](https://github.com/krishna-aditi/Sevir-Lambda-APIs/blob/main/reports/figures/dashboard_full.png)
Fig. Data Studio dashboard embedded on Streamlit interface

#### References
1. https://fastapi.tiangolo.com/tutorial/first-steps/
2. https://www.youtube.com/watch?v=1zMQBe0l1bM&ab_channel=AbhishekThakur
3. https://stackoverflow.com/questions/41228209/making-gif-from-images-using-imageio-in-python
4. https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app
5. https://www.philschmid.de/serverless-bert-with-huggingface-aws-lambda-docker
6. https://github.com/philschmid/serverless-bert-huggingface-aws-lambda-docker
7. https://www.thepythoncode.com/article/text-summarization-using-huggingface-transformers-python

Project Organization
------------

    ├── LICENSE
    ├── Makefile           <- Makefile with commands like `make data` or `make train`
    ├── README.md          <- The top-level README for developers using this project.
    │
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    │
    ├── reports            <- Screenshots
    │   ├── figures
    |
    ├── requirements.txt   <- The requirements file for reproducing the analysis environment
    │
    ├── setup.py           <- makes project pip installable (pip install -e .) so src can be imported
    |
    ├── src                <- Source code for use in this project.
    │   ├── __init__.py    <- Makes src a Python module
    │   │
    │   ├── data           <- Scripts to download or generate data
    │   │   ├── nowcast_api.py
    │   │   ├── nowcast_helper.py
    │   │   ├── nowcast_main.py
    │   │   ├── nowcast_utils.py
    │   │   ├── app.yaml
    │   │   ├── streamlit-app.py
    │   │   ├── sevir-ner
    |   |   |    ├── handler.py
    |   |   |    ├── get-model.py
    |   |   |    ├── requirements.txt
    |   |   |    └── serverless.yml
    |   |   |
    │   │   └── summary-api
    |   |       ├── handler.py
    |   |       ├── get-model.py
    |   |       ├── requirements.txt
    |   |       └── serverless.yml
    │   │
    │
    └── tox.ini            <- tox file with settings for running tox; see tox.readthedocs.io
 

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>

--------

#### Submitted by:

![image](https://user-images.githubusercontent.com/37017771/153502035-dde7b1ec-5020-4505-954a-2e67528366e7.png)

#### **Contribution:**
Aditi Krishna - 40%
Sushrut Mujumdar - 30% 
Abhishek Jaiswal - 30%

#### **Attestation:**

WE ATTEST THAT WE HAVEN’T USED ANY OTHER STUDENTS’ WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK. 

#### **Attestation for BERT tutorial:**
We attest that every group member implemented the BERT tutorial on AWS.

