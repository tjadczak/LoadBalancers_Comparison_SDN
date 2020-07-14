#include "url.h"
#include <string.h>
#include <stdlib.h>



// ---------------- CUrl ----------------

CUrl::CUrl()
{
    host = NULL;
    port = 80;
    path = NULL;
}

CUrl::~CUrl()
{
    delete [] host;
    delete [] path;
}

int CUrl::parse(const char* url)
{
    const char* p = url;
    const char* p2;
    const char* p3;
    const char* p4;
    delete [] host;
    delete [] path;
    if(strnicmp(url, "http://", 7) == 0)
        p += 7;


    p3 = strchr(p, ':');
    p2 = strchr(p, '/');
    p4 = p2;

    if(p3)
    {
	p4 = p3;
	port = atoi(++p3);
    }

    if(p4)
    {
        host = new char[p4 - p + 1];
        strncpy(host, p, p4 - p);
        host[p4-p] = 0;
    }
    else
    {
        host = new char[strlen(p) + 1];
        strcpy(host, p);
    }

    if(p2)
    {
        path = new char[strlen(p2) + 1];
        strcpy(path, p2);
    }
    else
    {
        path = new char[2];
        strcpy(path, "/");
    }

    return get_address(host, port, &addr);
}

CUrl& CUrl::operator=(const CUrl& r)
{
    delete [] host;
    delete [] path;
    host = new char[strlen(r.host) + 1];
    strcpy(host, r.host);
    port = r.port;
    path = new char[strlen(r.path) + 1];
    strcpy(path, r.path);
    addr = r.addr;
    return *this;
}

/** Changes the path part of the url */
void CUrl::setPath(const char* newpath)
{
    delete [] path;
    path = new char[strlen(newpath) + 1];
    strcpy(path, newpath);
}
