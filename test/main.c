#include <stdio.h>
#include "hello.h"
#include "goodbye/goodbye.h"

int
main(int argc, char *argv[])
{
	printf("%s", hello());
	printf("%s", goodbye());
	return 0;
}
