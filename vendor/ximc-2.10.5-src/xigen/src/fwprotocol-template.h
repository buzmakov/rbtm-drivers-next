#ifndef _FWPROTOCOL_H
#define _FWPROTOCOL_H

typedef struct
{
  INT32U	Cmd;
  INT8U		SendBytes;
  INT8U		ReceiveBytes;
} CmdLengthStr;

extern CmdLengthStr CmdLengths[];

#if defined(__cplusplus)
extern "C"
{
#endif

#pragma pack(push, 1)

/* @@GENERATED_CODE@@ */

#pragma pack(pop)

#if defined(__cplusplus)
};
#endif

#endif // _FWPROTOCOL_H

// vim: ts=4 shiftwidth=4
