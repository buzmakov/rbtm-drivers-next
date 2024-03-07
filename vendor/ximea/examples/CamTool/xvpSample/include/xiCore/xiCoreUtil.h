#ifndef UTIL_H
#define UTIL_H

#include <PicBuf.h>
#include <xiApi.h>

XICORE_API uint xiCore_GetChannelsCountForXiImageFormat(XI_IMG_FORMAT eFormat);

XICORE_API ExImageDataType xiCore_GetImageDataTypeForXiImageFormat(XI_IMG_FORMAT eFormat, uint uiTransportFormatBpc = 0);

XICORE_API ExDataStorageFormat xiCore_GetDataStorageFormatForXiImageFormat(XI_IMG_FORMAT eFormat);

XICORE_API ExColorFilterArray xiCore_ColorFilterArrayFromXiCfa(XI_COLOR_FILTER_ARRAY eCfa);

XICORE_API bool xiCore_IsRgbForXiImageFormat(XI_IMG_FORMAT eFormat);

XICORE_API XI_IMG_FORMAT xiCore_GetXiImgFormatForPicBufInfo(const SxPicBufInfo &picInfo);

#endif // UTIL_H
