

//-------------------------------------------------------------------------------------------------------------------
// xiApi_DNG_store header file
#ifndef __XIAPI_DNG_STORE_H
#define __XIAPI_DNG_STORE_H

#include <stdio.h>
#ifdef WIN32
  #include "xiApi.h"       // Windows
#else
  #include <m3api/xiApi.h> // Linux, OSX
#endif

#ifdef XIAPI_DNG_STORE_LIBRARY
  #define XIAPI_DNG_STORE __declspec(dllexport)
#else
  #define XIAPI_DNG_STORE __declspec(dllimport)
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Information about the image written to DNG file. It is recommended to call
// xidngInitMetadataStruct or xidngFillMetadataFromCameraParams before using it.
typedef struct _tagXI_DNG_METADATA
{
    // required parameters
    XI_COLOR_FILTER_ARRAY cfa;      // bayer matrix type
    int maxPixelValue;              // maximum pixel value, important for 16-bit image formats (i.e. 255 for 8-bit formats)

    // optional parameters
    char cameraModelName[256];      // camera model name, encoded in UTF8
    char cameraSerialNumber[256];
    char cameraUserId[256];         // camera ID given by the user, encoded in UTF8
    int autoExposureOn;             // 1: on, 0: off, -1: N/A
    int autoWhiteBalanceOn;         // 1: on, 0: off, -1: N/A
    float whiteBalanceR, whiteBalanceG, whiteBalanceB;     // white balance coefficients
    float lensAperture;
    float lensFocalLength;
    int acqTimeYear, acqTimeMonth, acqTimeDay, acqTimeHour, acqTimeMinute, acqTimeSecond;   // acquisition time

} XI_DNG_METADATA;

//-------------------------------------------------------------------------------------------------------------------
// Functions for storing image to DNG file format

/**
   \brief Saves the image into the file in DNG image file format. Does not support images in planar RGB and Transport formats.

   @param[in] filename                  filename to write to
   @param[in] img                       image data
   @param[in] metadata                  additional image information
   @return XI_OK when success, error value otherwise.
 */
XIAPI_DNG_STORE XI_RETURN __cdecl xidngStore(IN const char *filename, IN const XI_IMG *img, IN const XI_DNG_METADATA *metadata);

/**
   \brief Fills metadata structure with undefined values for optional parameters.

   @param[in] metadata                  structure to initialize
 */
XIAPI_DNG_STORE void __cdecl xidngInitMetadataStruct(IN XI_DNG_METADATA *metadata);

/**
   \brief Fills entire metadata structure with current camera parameter values obtained from xiGetParam calls.

   @param[in] metadata                  structure to initialize
 */
XIAPI_DNG_STORE void __cdecl xidngFillMetadataFromCameraParams(IN HANDLE hDevice, IN XI_DNG_METADATA *metadata);


#ifdef __cplusplus
}
#endif

#endif // __XIAPI_DNG_STORE_H
