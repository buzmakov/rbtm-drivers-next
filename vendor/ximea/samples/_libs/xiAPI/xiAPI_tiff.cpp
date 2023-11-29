// this library is able to save xiAPI image into TIFF file

#include <stdio.h>
#include <memory.h>
#if defined (_WIN32)
#include <xiApi.h>       // Windows
#include <libtiff/tiffio.h>
#else
#include <m3api/xiApi.h> // Linux, OSX
#include <tiffio.h>
#endif

void xiImageGetBitCount(XI_IMG* image, int* bit_count, int* num_channels)
{
	switch (image->frm)
	{
	case XI_MONO8:
	case XI_RAW8:
		*bit_count = 8;
		*num_channels = 1;
		break;
	case XI_MONO16:
	case XI_RAW16:
		*bit_count = 16;
		*num_channels = 1;
		break;
	case XI_RGB24:
		*bit_count = 8;
		*num_channels = 3;
		break;
	case XI_RAW32:
		*bit_count = 32;
		*num_channels = 1;
		break;
	case XI_RGB32:
		*bit_count = 8;
		*num_channels = 4;
		break;
	case XI_RAW32FLOAT:
		*bit_count = 32;
		*num_channels = 1;
		break;
	case XI_RGB48:
		*bit_count = 16;
		*num_channels = 3;
		break;
	case XI_RGB64:
		*bit_count = 16;
		*num_channels = 4;
		break;
	default:
		throw("xiImageGetBitCount - Unsupported data format\n");
	}
}

void WriteImage(XI_IMG* image, char* filename)
{
	TIFF* tiff_img = TIFFOpen(filename, "w");
	if (!tiff_img)
		throw "Opening image by TIFFOpen";

	// set tiff tags
	int width = image->width;
	int height = image->height;
	int bits_per_sample = 1;
	int num_channels = 1;
	int line_len = 0;

	xiImageGetBitCount(image, &bits_per_sample, &num_channels);
	line_len = width * ((bits_per_sample / 8) * num_channels);
	printf("Saving image %dx%d to file:%s\n", width, height, filename);

	int padding = image->padding_x / (bits_per_sample / 8);

	TIFFSetField(tiff_img, TIFFTAG_IMAGEWIDTH, width + padding);
	TIFFSetField(tiff_img, TIFFTAG_IMAGELENGTH, height);
	TIFFSetField(tiff_img, TIFFTAG_SAMPLESPERPIXEL, num_channels);
	TIFFSetField(tiff_img, TIFFTAG_BITSPERSAMPLE, bits_per_sample);
	TIFFSetField(tiff_img, TIFFTAG_MINSAMPLEVALUE, 0);
	TIFFSetField(tiff_img, TIFFTAG_MAXSAMPLEVALUE, (1 << bits_per_sample) - 1);
	TIFFSetField(tiff_img, TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT);
	TIFFSetField(tiff_img, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
	if (XI_RGB24 == image->frm || XI_RGB32 == image->frm)
		TIFFSetField(tiff_img, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB);
	else
		TIFFSetField(tiff_img, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK);
	TIFFSetField(tiff_img, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
	TIFFSetField(tiff_img, TIFFTAG_SAMPLEFORMAT, SAMPLEFORMAT_UINT);
	TIFFSetField(tiff_img, TIFFTAG_ROWSPERSTRIP, height);

	// save data
	if (TIFFWriteEncodedStrip(tiff_img, 0, image->bp, line_len*height) == -1)
	{
		throw("ImageFailed to write image");
	}

	TIFFWriteDirectory(tiff_img);
	TIFFClose(tiff_img);
}
