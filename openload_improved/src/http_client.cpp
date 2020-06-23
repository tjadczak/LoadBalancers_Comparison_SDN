#include "http_client.h"
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>

#ifndef WIN32

int stricmp(const char* s1, const char* s2)
{
    int res = 0;
    while(1)
    {
        res = tolower(*s1) - tolower(*s2);
        if(res != 0)
            break;
        if(*s1 == 0 || *s2 == 0)
            break;
        s1++;
        s2++;
    }
    return res;
}

int strnicmp(const char* s1, const char* s2, int n)
{
    int res = 0;
    while(n)
    {
        n--;
        res = tolower(*s1) - tolower(*s2);
        if(res != 0)
            break;
        if(*s1 == 0 || *s2 == 0)
            break;
        s1++;
        s2++;
    }
    return res;
}

#endif // WIN32

#define MAX_LINE_SIZE 2000
#define BUFFER_SIZE 2000

// ---------------- CHttpRequest ----------------

CHttpRequest::CHttpRequest()
{
    m_Method = METHOD_GET;
    m_Body = NULL;
}

CHttpRequest::~CHttpRequest()
{
    delete [] m_Body;
}

// ---------------- CHttpResponse ----------------

CHttpResponse::CHttpResponse()
{
    m_Status = 0;
    m_Body = NULL;
}

CHttpResponse::~CHttpResponse()
{
    delete [] m_Body;
}


// ================================================

void SendCommand(CTcpSock* pSock);
void SendHeader(CTcpSock* pSock);
void SendBody(CTcpSock* pSock);
void ReadStatus(CTcpSock* pSock);
void ParseStatus(CTcpSock* pSock);
void ReadHeader(CTcpSock* pSock);
void NonChunkedCtLenDone(CTcpSock* pSock);
void NonChunkedNoCtLenDone(CTcpSock* pSock);
void GotChunkLen(CTcpSock* pSock);
void GotChunk(CTcpSock* pSock);
void Done(CTcpSock* pSock);

int SendRequest(CHttpRequest* pReq, CEventLoop* pEvLoop, TResponseFunc* pCallBack, void* pParam)
{
    int res = 0;

    // create socket and context
    CTcpSock* pSock = new CTcpSock;
    CHttpContext* pContext = new CHttpContext;
    pContext->m_pSock = pSock;
    pContext->m_pReq = pReq;
    pContext->m_pResp = new CHttpResponse;
    pContext->m_pEvLoop = pEvLoop;
    pContext->m_pCallBack = pCallBack;
    pContext->m_pParam = pParam;
    pSock->m_context = pContext;
    res = pSock->create();
    if(res)
        return res;

    // add socket to the event loop
    pEvLoop->addSock(pSock);

    // get ready to send command
    pSock->m_cbConnectOk = SendCommand;

    // start connecting
    res = pSock->connect(&pReq->m_Url.addr);

    return res;
}

void SendCommand(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;

    // check what method to use
    char* meth;
    if(pContext->m_pReq->m_Method == METHOD_GET)
        meth = "GET ";
    if(pContext->m_pReq->m_Method == METHOD_POST)
        meth = "POST ";
    if(pContext->m_pReq->m_Method == METHOD_HEAD)
        meth = "HEAD ";

    // allocate buffer for the command
    char* command = new char[20 + strlen(pContext->m_pReq->m_Url.path)];
    command[0] = 0;

    // create the command as 'method path HTTP/1.1CRLF'
    strcat(command, meth);
    strcat(command, pContext->m_pReq->m_Url.path);
    strcat(command, " HTTP/1.1" CRLF);

    // set connection header to close
    pContext->m_pReq->m_pHeaders->Add("Connection", "Close");
    // make sure we have a host header
    if(pContext->m_pReq->m_pHeaders->Find("Host") == NULL)
        pContext->m_pReq->m_pHeaders->Add("Host", pContext->m_pReq->m_Url.host);
    
    // get ready to send the first header
    pContext->m_pHeader = pContext->m_pReq->m_pHeaders->pFirst;
    pSock->m_cbSendOk = SendHeader;

    // send the command
    pSock->sendString(command);
}

void SendHeader(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;
    // free last send buf
    delete [] (char*) pSock->m_wbuf;

    // allocate buffer for the header line
    char* hdr = new char [10 + strlen(pContext->m_pHeader->name) +
        strlen(pContext->m_pHeader->value)];
    hdr[0] = 0;

    // create header line as 'name: valueCRLF'
    strcat(hdr, pContext->m_pHeader->name);
    strcat(hdr, ": ");
    strcat(hdr, pContext->m_pHeader->value);
    strcat(hdr, CRLF);

    // set context to point to next header
    pContext->m_pHeader = pContext->m_pHeader->pNext;

    if(pContext->m_pHeader == NULL)
    {
        // if there are no more headers send an extra CRLF
        strcat(hdr, CRLF);
        // if this is POST get ready to send body
        // otherwise to read status
        if(pContext->m_pReq->m_Method == METHOD_POST)
            pSock->m_cbSendOk = SendBody;
        else
            pSock->m_cbSendOk = ReadStatus;
    }

    // send the header
    pSock->sendString(hdr);
}

void SendBody(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;
    // free last send buf
    delete [] (char*) pSock->m_wbuf;

    // get ready to read status
    pSock->m_cbSendOk = ReadStatus;

    // send the body
    pSock->send(pContext->m_pReq->m_Body, pContext->m_pReq->m_Len);
}

void ReadStatus(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;
    // free last send buf
    delete [] (char*) pSock->m_wbuf;

    // allocate line bufffer
    char *buf = new char[MAX_LINE_SIZE];

    // get ready to parse status
    pSock->m_cbReadLineOk = ParseStatus;

    pSock->readLine(buf, MAX_LINE_SIZE);
}

void ParseStatus(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;

    char* p;
    char* buf = pSock->m_rbuf;

    p = strstr(buf, "HTTP/1.1");
    if(p)
    {
        p += 8;
        while(isspace(*p) && *p)
            p++;
        pContext->m_pResp->m_Status = atoi(p);
    }
    else
    {
        p = buf;
        while(!isspace(*p) && *p)
            p++;
        while(isspace(*p) && *p)
            p++;
        pContext->m_pResp->m_Status = atoi(p);
    }


    // get ready to read more headers
    pSock->m_cbReadLineOk = ReadHeader;

    // read first header
    pSock->readLine(buf, MAX_LINE_SIZE);
}

void ReadHeader(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;

    if(pSock->m_read == 0)
    {
        // got an empty line, done with reading headers
        // delete the line buf
        delete [] pSock->m_rbuf;

        // check if body is chunked
        bool isChunked = false;
        const char* transfer_encoding = pContext->m_pResp->m_Headers.FindValue("Transfer-Encoding");
        if(transfer_encoding && stricmp(transfer_encoding, "chunked") == 0)
            isChunked = true;

        if(isChunked)
        {
            // set start len to 0
            pContext->m_pResp->m_Len = 0;

            // get ready to get chunk len
            pSock->m_cbReadLineOk = GotChunkLen;

            // allocate linebuf
            char* line = new char[MAX_LINE_SIZE];

            // read first chunk len
            pSock->readLine(line, MAX_LINE_SIZE);
        }
        else
        {
            // get content length
            const char* content_length = pContext->m_pResp->m_Headers.FindValue("Content-Length");
            if(content_length)
            {
                int len = atoi(content_length);
                pContext->m_pResp->m_Body = new char[len];
                pSock->m_cbRecvBufOk = NonChunkedCtLenDone;
                pSock->recvBuf(pContext->m_pResp->m_Body, len);
            }
            else
            {
                // handle when content-length header is not set
                pContext->m_pResp->m_Body = new char[BUFFER_SIZE];
                pContext->m_pResp->m_Len = 0;
                pSock->m_cbRecvBufOk = NonChunkedNoCtLenDone;
                pSock->recvBuf(pContext->m_pResp->m_Body, BUFFER_SIZE);
            }
        }

    }
    else
    {
        // add header to the response object
        pContext->m_pResp->m_Headers.Add(pSock->m_rbuf);
        // read next header
        pSock->readLine(pSock->m_rbuf, MAX_LINE_SIZE);
    }

}

void NonChunkedCtLenDone(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;

    // set actual read len
    pContext->m_pResp->m_Len = pSock->m_read;

    Done(pSock);
}

void NonChunkedNoCtLenDone(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;

    // updated len read
    pContext->m_pResp->m_Len += pSock->m_read;

    // check if we are done
    if(pSock->m_read < BUFFER_SIZE)
    {
        Done(pSock);
    }
    else
    {
        // extend buffer
        char* pData;
        pData = new char[pContext->m_pResp->m_Len + BUFFER_SIZE];
        memcpy(pData, pContext->m_pResp->m_Body, pContext->m_pResp->m_Len);
        delete [] pContext->m_pResp->m_Body;
        pContext->m_pResp->m_Body = pData;

        pSock->m_cbRecvBufOk = NonChunkedNoCtLenDone;
        pSock->recvBuf(&pData[pContext->m_pResp->m_Len], BUFFER_SIZE);
    }
}

void GotChunkLen(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;

    // get ready for reading chunk
    pSock->m_cbRecvBufOk = GotChunk;

    // get the chunk len
    unsigned long chunkLen;
    chunkLen = strtoul(pSock->m_rbuf, 0, 16);

    // delete the line buf
    delete [] pSock->m_rbuf;

    // check if we are done
    if(chunkLen == 0)
    {
        Done(pSock);
        return;
    }

    // allocate space including his chunk
    char* p = new char[pContext->m_pResp->m_Len + chunkLen];

    // copy old data if necessary
    if(pContext->m_pResp->m_Len > 0)
    {
        memcpy(p, pContext->m_pResp->m_Body, pContext->m_pResp->m_Len);
        delete [] pContext->m_pResp->m_Body;
    }
    pContext->m_pResp->m_Body = p;

    // read the chunk
    pSock->recvBuf(&p[pContext->m_pResp->m_Len], chunkLen);
        
}

void GotChunk(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;

    // update total size
    pContext->m_pResp->m_Len += pSock->m_read;

    // check if the socket was closed at the other end
    if(pSock->m_eof)
    {
        Done(pSock);
        return;
    }

    // allocate linebuf
    char* line = new char[MAX_LINE_SIZE];

    // read chunk len
    pSock->readLine(line, MAX_LINE_SIZE);
}

void Done(CTcpSock* pSock)
{
    CHttpContext* pContext = (CHttpContext*) pSock->m_context;

    // remove sock from event loop
    pContext->m_pEvLoop->removeSock(pSock);

    // delayed delete (and implicit close) socket
    pSock->deleteSock();

    // make call back
    if(pContext->m_pCallBack)
        (*pContext->m_pCallBack)(pContext);

    // cleanup
    delete pContext->m_pResp;
    delete pContext;
}

