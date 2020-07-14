/***************************************************************************
                          tmplparmchunk.h  -  description
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

#ifndef TMPLPARMCHUNK_H
#define TMPLPARMCHUNK_H

#include "tmplchunk.h"

/**A parameter chunk
  *@author pelle
  */

class CTmplParmChunk : public CTmplChunk  {
public: 
    CTmplParmChunk();
    ~CTmplParmChunk();
    /** compares that the parm is present at pos */
    int Verify(const char*& pos, const char* parm);
    /** dump the param chunk */
    void Dump();
};

#endif
