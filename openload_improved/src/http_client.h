#ifndef HTTP_CLIENT_H
#define HTTP_CLIENT_H

#include "sock.h"
#include "event_loop.h"
#include "url.h"
#include "http_headers.h"

#define CRLF "\x00d\x00a"

enum EHttpMethod
{
    METHOD_GET = 0,
    METHOD_POST = 1,
    METHOD_HEAD = 2,
    METHOD_PUT = 3,
    METHOD_DELETE = 4
};

class CHttpRequest
{
public:
    CHttpRequest();
    virtual ~CHttpRequest();

    EHttpMethod m_Method;
    CUrl m_Url;
    CHttpHeaderList* m_pHeaders;
    char* m_Body;
    int m_Len;
};

class CHttpResponse
{
public:
    CHttpResponse();
    virtual ~CHttpResponse();

    int m_Status;
    CHttpHeaderList m_Headers;
    char* m_Body;
    int m_Len;
};

class CHttpContext;

typedef void TResponseFunc(CHttpContext* pContext);

class CHttpContext
{
public:
    CTcpSock* m_pSock;
    CHttpRequest* m_pReq;
    CHttpResponse* m_pResp;
    CHttpHeader* m_pHeader;
    CEventLoop* m_pEvLoop;
    TResponseFunc* m_pCallBack;
    void* m_pParam;
};



int SendRequest(CHttpRequest* pReq, CEventLoop* pEvLoop, TResponseFunc* pCallBack, void* pParam);

#endif // HTTP_CLIENT_H

