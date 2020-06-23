#ifndef EVENT_LOOP_H_INCLUDED
#define EVENT_LOOP_H_INCLUDED

#include "sock.h"

class CSockList;

class CEventLoop
{
public:
    CEventLoop(void);
    ~CEventLoop(void);
    int run(void);
    void stop(void);
    void addSock(CTcpSock* sock);
    void removeSock(CTcpSock* sock);
protected:
    CSockList* m_sockList;
    int m_bContinue;
};

#endif // EVENT_LOOP_H_INCLUDED

