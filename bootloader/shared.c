
#include "kobold/appctl.h"
#include "kobold/crc.h"

__attribute__((section(".kobold.ram.appctl")))
struct kobold_appctl_data kobold_appctl;

__attribute__((section(".kobold.flash.crc")))
struct kobold_crc_data kobold_crc;
