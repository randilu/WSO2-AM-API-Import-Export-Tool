#!/usr/bin/python
import sys
import requests
import datetime
import time
import json
import os
import zipfile
import git
import base64

def main(argv):
    apiKey = argv[0]
    apiSecret = argv[1]
    userName = argv[2]
    userPassword = argv[3]
    hostName = argv[4]
    tokenEndpointPort = argv[5]
    restApiEndpointPort = argv[6]
    gitRepoPath = argv[7]
    
    (accessToken, expiresIn, refreshToken) = getAccessToken(apiKey, apiSecret, userName, userPassword, hostName, tokenEndpointPort)
    apiList = getAllApis(hostName,restApiEndpointPort, accessToken)
    exportAllApis(hostName, apiList, gitRepoPath)
    unzipAllFile(gitRepoPath)
    gitPushAllApis(gitRepoPath)


def getAccessToken(apiKey, apiSecret, userName, userPassword, hostName, tokenEndpointPort):
    stsUrl = getTokenEndpoint(hostName, tokenEndpointPort)
    payload= {'client_id' : apiKey,'client_secret':apiSecret, 'username':userName, 'password':userPassword, 'grant_type':'password', 'scope':'apim:api_view'}
    
    response = requests.post(stsUrl, data=payload, verify=False)
    if response.status_code == 200:
        data = json.loads(response.text)
        accessToken = data['access_token']
        expiresIn = data['expires_in'] #in seconds
        refreshToken = data['refresh_token']
        return (accessToken, expiresIn, refreshToken)
    else:
        print 'Failed to obtain access token, status code ' + str(response.status_code)
        return ('', '0', '')


def getAllApis(hostName, restApiEndpointPort, accessToken):
    stsUrl = getImpExpEndpoint(hostName, restApiEndpointPort) + "/" + "apis"
    headers = {'Authorization': 'Bearer ' + accessToken}

    response = requests.get(stsUrl, headers=headers)
    data = json.loads(response.text)
    apiList = []
    for x in range(0, data['count']):
        apiList.append((data['list'][x]['name'], data['list'][x]['version']))
    return apiList


def exportAllApis(hostName, port, userName, userPassword, apiList, gitRepoPath):
    for x in range(0, len(apiList)):
        zipFileName = gitRepoPath + "/" + apiList[x][0] + "-" + apiList[x][1] + ".zip"
        importExportEndpoint = getImpExpEndpoint(hostName, port)
        exportUrl = importExportEndpoint + '?name=' + apiList[x][0] + '&version=' + apiList[x][1] + '&provider=admin'
        headers = getAuthHeaders(userName, userPassword)
        with open(zipFileName, 'wb') as handle:
            response = requests.get(exportUrl, headers=headers, verify=False, stream=True)
            if not response.ok:
                print response

            for block in response.iter_content(1024):
                handle.write(block)

    return True

def unzipAllFile(gitRepoPath):
    extension = ".zip"
    os.chdir(gitRepoPath)
    for item in os.listdir(gitRepoPath):
        if item.endswith(extension):
            file_name = os.path.abspath(item)
            zip_ref = zipfile.ZipFile(file_name)
            zip_ref.extractall(gitRepoPath)
            zip_ref.close()
            os.remove(file_name)
    return True

def gitPushAllApis(gitRepoPath):
    repo = git.Repo(gitRepoPath)
    repo.git.add('*')
    gitStatus = repo.git.status()
    print gitStatus

    if gitStatus.find("nothing to commit") > -1:
        repo.git.push()
    else:
        repo.git.commit( m='Added new API Changes' )
        repo.git.push()
    print repo.git.status()

    return True

def getImpExpEndpoint(hostName, restApiEnpointPort):
    endPoint = 'https://' + hostName + ':' + restApiEnpointPort + '/api-import-export-2.0.0-SNAPSHOT/import-api'
    return endPoint

def getRestApiEndpoint(hostName, restApiEnpointPort):
    endPoint = 'https://' + hostName + ':' + restApiEnpointPort + '/api/am/publisher/v0.9/'
    return endPoint

def getTokenEndpoint(hostName, tokenEnpointPort):
    endPint = 'https://' + hostName + ':' + tokenEnpointPort + '/token'
    return endPint

def getAuthHeaders(userName, userPassword):
    headerValue = base64.b64encode(userName + ':' + userPassword)
    headers = "{'Authorization': 'Basic " + headerValue + "'}"
    return headers

if __name__ == '__main__':
    if len(sys.argv) != 6:
        print "Usage: python export-api.py apiKey, apiSecret, userName, password hostName"
        sys.exit(1)
    main(sys.argv[1:])
