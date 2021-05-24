#include "interface.h"

// Variables for reading
bool newData = false;
char commandIn[numChars];
uint8_t commandType = 0;
char readCommand[numChars];
char axis = 'z';
float value = -1.0;

void recieve()
{
    static uint8_t idx = 0;
    char queryMarker = '?';
    char cmdMarker = '!';
    char endMarker = '\r';
    char rc;

    while (Serial.available() > 0 && newData == false)
    {
        rc = Serial.read();

        if (commandType != NONE)
        {

            if (rc != endMarker)
            {
                commandIn[idx] = rc;
                idx++;
                if (idx >= numChars)
                {
                    idx = numChars - 1;
                }
            }
            else
            {
                commandIn[idx] = '\0'; // terminate the string
                idx = 0;
                newData = true;
            }
        }

        else if (rc == queryMarker)
        {
            commandType = QUERY;
            // Serial.println("Set QUERY");
        }
        else if (rc == cmdMarker)
        {
            commandType = COMMAND;
            // Serial.println("Set COMMAND");
        }
    }
    if (newData == true)
    {
        strcpy(readCommand, commandIn); // Preserves integrity of received command
    }
}

void parse()
{
    char *strtokIdx;                      // Keep track of the strtok position as a pointer
    strtokIdx = strtok(readCommand, ","); // retun the first token (split on comma)

    axis = *strtokIdx; // assign first token to axis value

    if (commandType == COMMAND)
    {                                  // Only look for a value if we are expecting it
        strtokIdx = strtok(NULL, ","); // get the second token (split on comma)
        value = atof(strtokIdx);       // convert the second token to a float
    }
    else
        value = -1.0;
}

void respond(char *response)
{
    Serial.print('<');
    Serial.print(response);
    Serial.println('>');
}
