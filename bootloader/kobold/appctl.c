
#include "appctl.h"

int kobold_appctl_run(void *data_)
{
	struct kobold_appctl_data *data = data_;
	return data->magic == KOBOLD_APPCTL_MAGIC ?
		KOBOLD_APPCTL_OUTCOME_FLASH : KOBOLD_APPCTL_OUTCOME_CONTINUE;
}
