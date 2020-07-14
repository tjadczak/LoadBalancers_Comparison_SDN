/***************************************************************************
                          tmplchunk.h  -  description
                             -------------------
    begin                : Mon Jun 25 2001
    copyright            : (C) 2001 by pelle
    email                : pelle@localhost.localdomain
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

#ifndef TMPLCHUNK_H
#define TMPLCHUNK_H


/**A chunk of the template, either text or parameter to be substituted
  *@author pelle
  */

class CTmplChunk {
public: 
    CTmplChunk();
    virtual ~CTmplChunk();
    /** Appends this chunk to the end of the list with the given start and end vars */
    void Append(CTmplChunk*& pStart, CTmplChunk*& pEnd);
    /** verifies this chunk against the data given by pos and parm.
     *  pos is incremented by the length of the chunk */
    virtual int Verify(const char*& pos, const char* parm);
    /** dump the chunk list */
    virtual void Dump();
public: // Public attributes
    /** Link to the next chunk */
    CTmplChunk* m_pNext;
};

#endif
