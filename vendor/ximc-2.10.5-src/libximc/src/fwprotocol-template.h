#ifndef INC_FWPROTOCOL_H
#define INC_FWPROTOCOL_H

typedef struct
{
  INT32U	Cmd;
  INT8U		SendBytes;
  INT8U		ReceiveBytes;
} CmdLengthStr;

extern CmdLengthStr CmdLengths[];

#pragma pack(push, 1)

/* @@GENERATED_CODE@@ */

#pragma pack(pop)

#endif // INC_FWPROTOCOL_H

// vim: ts=4 shiftwidth=4
