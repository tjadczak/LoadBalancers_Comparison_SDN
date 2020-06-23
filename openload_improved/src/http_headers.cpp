#include "http_headers.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>

#ifndef WIN32

extern int stricmp(const char* s1, const char* s2);
extern int strnicmp(const char* s1, const char* s2, int n);

#endif // WIN32


// ---------------- CHttpHeader ----------------

CHttpHeader::CHttpHeader()
{
    name = NULL;
    value = NULL;
    pNext = NULL;
    pPrev = NULL;
}

CHttpHeader::~CHttpHeader()
{
    delete [] name;
    delete [] value;
}

void CHttpHeader::Set(const char* n, const char* v)
{
    name = new char[strlen(n) + 1];
    strcpy(name, n);
    value = new char[strlen(v) + 1];
    strcpy(value, v);
}


// ---------------- CHttpHeaderList ----------------

CHttpHeaderList::CHttpHeaderList()
{
    pFirst = NULL;
    pLast = NULL;
}

CHttpHeaderList::~CHttpHeaderList()
{
    while(pFirst)
    {
        pLast = pFirst->pNext;
        delete pFirst;
        pFirst = pLast;
    }
}

void CHttpHeaderList::Insert(CHttpHeader* pNew)
{
    pNew->pPrev = pLast;
    if(pLast)
        pLast->pNext = pNew;
    pLast = pNew;

    if(pFirst == NULL)
        pFirst = pNew;
}

void CHttpHeaderList::Add(const char* name, const char* value)
{
    CHttpHeader* pNew;
    pNew = Find(name);
    if(pNew)
    {
        delete [] pNew->value;
        pNew->value = new char[strlen(value) + 1];
        strcpy(pNew->value, value);
    }
    else
    {
        pNew = new CHttpHeader();
        pNew->Set(name, value);
        Insert(pNew);
    }
}

void CHttpHeaderList::Add(const char* line)
{
    const char* p = line;
    const char* pColon;
    char* name;
    char* value;

    // skip leading spaces
    while(isspace(*p))
        p++;

    // find colon
    pColon = strchr(p, ':');
    if(pColon)
    {
        name = new char[pColon - p + 1];
        strncpy(name, p, pColon - p);
        name[pColon - p] = 0;

        // skip spaces after colon
        p = pColon;
        p++;
        while(isspace(*p))
            p++;

        value = new char[strlen(p) + 1];
        strcpy(value, p);

        CHttpHeader* pNew = Find(name);
        if(pNew)
        {
            delete [] pNew->value;
            pNew->value = value;
            delete [] name;
        }
        else
        {
            pNew = new CHttpHeader();
            pNew->name = name;
            pNew->value = value;
            Insert(pNew);
        }
    }

}

CHttpHeader* CHttpHeaderList::Find(const char* name)
{
    CHttpHeader* pFind = pFirst;
    while(pFind)
    {
        if(stricmp(pFind->name, name) == 0)
            return pFind;
        pFind = pFind->pNext;
    }
    return pFind;
}

const char* CHttpHeaderList::FindValue(const char* name)
{
    CHttpHeader* pFind = Find(name);
    if(pFind)
        return pFind->value;
    else
        return NULL;
}

void CHttpHeaderList::Delete(const char* name)
{
    CHttpHeader* pTmp = Find(name);
    if(pTmp)
    {
        if(pTmp->pNext)
            pTmp->pNext->pPrev = pTmp->pPrev;
        else
            pLast = pTmp->pPrev;

        if(pTmp->pPrev)
            pTmp->pPrev->pNext = pTmp->pNext;
        else
            pFirst = pTmp->pNext;

    }
}

void CHttpHeaderList::Dump()
{
    CHttpHeader* pTmp = pFirst;
    while(pTmp)
    {
        printf("%s: %s\n", pTmp->name, pTmp->value);
        pTmp = pTmp->pNext;
    }
}

