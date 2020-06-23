#ifndef HTTP_HEADERS_H
#define HTTP_HEADERS_H

class CHttpHeader
{
public:
    char* name;
    char* value;

    CHttpHeader();
    void Set(const char* n, const char* v);
    virtual ~CHttpHeader();

    CHttpHeader* pNext;
    CHttpHeader* pPrev;
};

class CHttpHeaderList
{
public:
    CHttpHeader* pFirst;
    CHttpHeader* pLast;

    CHttpHeaderList();
    virtual ~CHttpHeaderList();

    void Insert(CHttpHeader* pNew);
    void Add(const char* name, const char* value);
    void Add(const char* line);
    CHttpHeader* Find(const char* name);
    const char* FindValue(const char* name);
    void Delete(const char* name);

    void Dump();
};


#endif // HTTP_HEADERS_H

