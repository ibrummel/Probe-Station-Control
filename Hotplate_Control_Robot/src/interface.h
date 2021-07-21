#include <Arduino.h>

extern bool newData;
const uint8_t numChars = 32;
extern char commandIn[numChars];
extern uint8_t commandType;
extern char readCommand[numChars];
extern char axis;
extern float value;

enum COMMAND_TYPES {
    NONE = 0,
    QUERY = 1,
    COMMAND = 2
};

// Function Prototypes
void recieve ();
void parse();
void respond(char* response);