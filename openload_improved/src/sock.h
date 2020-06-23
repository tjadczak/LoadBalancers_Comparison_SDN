#ifndef SOCK_H_INCLUDED
#define SOCK_H_INCLUDED

#ifdef WIN32

#include <winsock.h>

#else // WIN32

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <netinet/in.h>
#include <arpa/inet.h>

typedef struct sockaddr_in SOCKADDR_IN;
typedef int SOCKET;

#endif // WIN32

class CTcpSock;

/**
 * The TCallBack type is used for all callbacks whenever the @ref CTcpSock
 * changes state.
 *
 * @param sock pointer to the socket object that changed state.
 */
typedef void TCallBack(CTcpSock* sock);

/**
 * Lookup an address consisting of host name (or IP) and port number.
 *
 * @param host The hostname or IP address in dot notaion, e.g. "192.168.0.1"
 * @param port port number
 * @param pAdr pointer to a variable for storing the result
 * @return zero on success
 */
int get_address(const char* host, int port, SOCKADDR_IN* pAdr);

/**
 * Retrieve the error code of the last failed socket operation.
 *
 * @return error code
 */
int getSocketError();

/**
 * The CTcpSock represents a socket used for asynchronous operation.
 *
 * When a CTcpSock has been created, it can be registered with an
 * @ref CEventLoop which passes 'events' from a select system
 * call to the socket object, whenever data arrives or the socket
 * is ready to recieve more data for writing.
 *
 * Handling of the events is implemented as a finite state machine.
 * Callbacks can be registered for whenever the socket changes state.
 * Callback function pointers are stored in the m_cb* member variables.
 *
 * @short This class represents an asynchronous TCP socket.
 * @see CEventLoop
 * @author Pelle Johnsen
 */
class CTcpSock
{
public:
    /**
     * Constructor which initializes datamembers.
     */
    CTcpSock(void);

    /**
     * Destructor which automatically closes the socket if it has
     * been connected.
     */
    ~CTcpSock(void);

    /**
     * Creates the socket, i.e. gets a socket handle ( @ref m_sock ).
     *
     * @return zero on success
     */
    int create(void);

    /**
     * Closes the socket if it has been connected. It is safe to call
     * close even if the socket wasn't created or connected.
     *
     * @return zero on success
     */
    int close(void);

    /**
     * Start connecting the socket to a remote peer. When the connect
     * completes the @ref m_cbConnectOk callback will be called.
     *
     * @param name address (host, port) of the remote peer
     * @return zero or EINPROGRESS on success
     */
    int connect(SOCKADDR_IN* name);

    /**
     * Start sending a buffer to the remote peer. When all bytes have
     * been send the @ref m_cbSendOk callback will be called.
     *
     * @param buf pointer to the buffer
     * @param len number of bytes to send
     * @return number of bytes sent so far
     */
    int send(const char* buf, int len);

    /**
     * Start sending a zero terminated string. When the whole string has
     * been sent the @ref m_cbSendOk callback will be called.
     * 
     * @param str the string to send
     * @return number of bytes sent so far
     */
    int sendString(const char* str);

    /**
     * Start receiving a buffer. When the desired number of bytes have
     * been read or the remote end has closed the socket, the
     * @ref m_cbRecvBufOk callback will be called.
     *
     * @param buf pointer to buffer for receiving data
     * @param len number of bytes to receive
     * @return zero on success
     */
    int recvBuf(char* buf, int len);

    /**
     * Start reading a line from the socket. When a full line have
     * been read or the remote end has closed the socket, the
     * @ref m_cbReadLineOk callback will be called.
     *
     * @param buf pointer to buffer for receiving data
     * @param max_len maximum number of bytes to read.
     * @return zero on success
     */
    int readLine(char* buf, int max_len);

    /**
     * Sets fd_sets for this socket depending on it's state. The fd_sets
     * are used by a @ref CEventLoop for the select system call. Basically
     * this socket indicates to the EventLoop if it is currently interested
     * in read, write or exception events.
     *
     * @param rfds read fd_set
     * @param wfds write fd_set
     * @param efds exception fd_set
     * @return zero on success
     */
    int setFdSets(fd_set* rfds, fd_set* wfds, fd_set* efds);

    /**
     * Checks fd_sets for this socket after the @ref CEventLoop returns
     * from the select system call, to see if there was any events for
     * this socket. If an event arrived @ref processEvent is called.
     * Before returning to the EventLoop any new internal events are
     * handled by calling the appropriate callback.
     *
     * @param rfds read fd_set
     * @param wfds write fd_set
     * @param efds exception fd_set
     * @return zero on success
     */
    int checkFdSets(fd_set* rfds, fd_set* wfds, fd_set* efds);

    /**
     * Ask the socket to delete itself, just before returning to the
     * EventLoop. This allows for 'nested' callbacks that needs
     * to delete the socket object.
     */
    void deleteSock(void);

    /**
     * The socket handle (i.e. file descriptor on UNIX)
     */
    SOCKET m_sock;

    /**
     * This is a pointer to some arbitrary context you can assign
     * to the socket. This is useful if you have one set of callback
     * functions which handle multiple sockets. They can use the context
     * data to figure out where the particular socket 'belong'
     */
    void* m_context;

    /**
     * Callback for when the socket has succesfully connected to the
     * remote peer.
     */
    TCallBack* m_cbConnectOk;

    /**
     * Callback for when a send or sendString has completed.
     */
    TCallBack* m_cbSendOk;

    /**
     * Callback for when a line has been read from the socket.
     */
    TCallBack* m_cbReadLineOk;

    /**
     * Callback for when a buffer has been received.
     */
    TCallBack* m_cbRecvBufOk;

    /**
     * Pointer to the buffer being written ( @ref send ,
     * @ref sendString ).
     */
    const char* m_wbuf;

    /**
     * Number of bytes to be sent.
     */
    int m_wlen;

    /**
     * Number of bytes actually sent (so far).
     */
    int m_sent;

    /**
     * Pointer to the buffer being read to ( @ref readLine ,
     * @ref recvBuf ).
     */
    char* m_rbuf;

    /**
     * Number of bytes to be read
     */
    int m_rlen;

    /**
     * Number of bytes actually read (so far).
     */
    int m_read;

    /**
     * Non-zero if the socket has been closed at the remote end.
     */
    int m_eof;

protected:
    /**
     * The different states of the socket
     */
    enum ESockStates
    {
        start,
        created,
        connecting,
        ready,
        sending,
        recievingBuf,
        readingLine,
        closed
    };

    ESockStates m_state;

    /**
     * Types of events received from the EventLoop
     */
    enum EEvents
    {
        read   = 1,
        write  = 2,
        except = 4
    };

    /**
     * Internal events used to do callbacks and delete the socket
     * before returning to the EventLoop, if needed.
     */
    enum ESockInternalEvents
    {
        noEvent,
        connectOk,
        sendOk,
        readLineOk,
        recvBufOk,
        deleteEvent
    };

    ESockInternalEvents m_intStatus;

    /**
     * Processes an event received from the EventLoop. Takes the
     * appropriate action depending on the current state ( @ref m_state ).
     *
     * @param event type of event: read, write, exception
     * @return zero on success
     */
    int processEvent(int event);

    /**
     * Called every time data arrives, when reading a line
     */
    void readLineLoop(void);

    /**
     * Called every time data arrives, when reading to a buffer
     */
    void recvBufLoop(void);
};

#endif // SOCK_H_INCLUDED
