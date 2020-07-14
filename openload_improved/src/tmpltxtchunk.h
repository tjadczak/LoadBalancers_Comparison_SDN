/***************************************************************************
                          tmpltxtchunk.h  -  description
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

#ifndef TMPLTXTCHUNK_H
#define TMPLTXTCHUNK_H

#include "tmplchunk.h"

/**A text chunk
  *@author pelle
  */

class CTmplTxtChunk : public CTmplChunk  {
public: 
    CTmplTxtChunk(const char* pos, long len);
    ~CTmplTxtChunk();
    /** Verifies this chunk by comparing against the text given by pos */
    int Verify(const char*& pos, const char* parm);
    /** dump the text chunk */
    void Dump();
protected: // Protected attributes
    /** the position (char pointer) in the template where this chunk starts */
    const char* m_Pos;
    /** Length of this chunk */
    long m_Len;
};

#endif
