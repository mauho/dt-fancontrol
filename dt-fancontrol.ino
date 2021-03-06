#include <Arduino.h>
#include <U8g2lib.h>

U8G2_SSD1306_128X32_UNIVISION_F_SW_I2C u8g2(U8G2_R0, SCL, SDA, U8X8_PIN_NONE);

// Functions
float readNTCTemp(int analogPin, int BValue);
byte getTargetPWM(float dt);
void setPwmDuty(byte duty);
void parseSerial();

// Constants
const byte OC1A_PIN = 9; // PWM Pin for fan to controll
const word PWM_FREQ_HZ = 25000; //Adjust this value to adjust the frequency
const word TCNT1_TOP = 16000000 / (2 * PWM_FREQ_HZ);
const int R = 10000; // R = 10KΩ -> voltage divider resistance

// Variables
unsigned long lastRefreshTime;
float RT, VR, ln, TX, T0, VRT, sExp, sRad, sAmb, deltaT, VCC;
float s_slope, s_attack; // sigmoid variables
byte  pwm, static_pwm;
int   s_min, s_max, readCount;

void setup() {
  Serial.begin(57600);
  u8g2.begin();
  u8g2.setBusClock(400000);

  pinMode(1, INPUT); // Sensor water temperature
  pinMode(2, INPUT); // Sensor ambient temperature
  pinMode(OC1A_PIN, OUTPUT);

  // Default number of readings prior to calculate and send PWM signal and data
  readCount = 631;

  // Default sigmoid parameters - see https://www.geogebra.org/calculator with file in project folder for visualization
  s_min = 18;     // minimum PWM level lift in order to prevent fans from stopping (changes with v)
  s_max = 100;    // maximum PWM level to be reached
  s_slope = -0.4; // slope -> how big deltaT has to be to reach a cerain pwm level
  s_attack = 6.0; // how far the sigmoid function is shifted to the right

  T0 = 25 + 273.15;  // Temperature T0 from datasheet, conversion from Celsius to kelvin

  // PWM Settings
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1  = 0;
  TCCR1A |= (1 << COM1A1) | (1 << WGM11);
  TCCR1B |= (1 << WGM13) | (1 << CS10);
  ICR1 = TCNT1_TOP; // set PWM Frequency
}

void loop() {
  // Check if commands were sent
  if (Serial.available() > 0) {
    parseSerial();
  }

  // Read temperatures
  sRad = readNTCTemp(1, 3976) - 0.7;
  sAmb = readNTCTemp(2, 3976) - 0.7;
  deltaT = (sRad - sAmb);

  // Calculate dT and PWM Value
  if (static_pwm > 0) {
    pwm = static_pwm;
  } else {
    pwm = getTargetPWM(deltaT);
  }

  // Set PWM Value
  setPwmDuty(pwm);

  // Print data to serial
  if (Serial) {
    Serial.print(sRad, 2);
    Serial.print(";");
    Serial.print(sAmb, 2);
    Serial.print(";");
    Serial.print(deltaT);
    Serial.print(";");
    Serial.println(pwm);
  }

  if (readCount < 10) {
    if (millis() - lastRefreshTime > 1000) {
      drawOLED();
      lastRefreshTime = millis();
    }
  } else {
    drawOLED();
    lastRefreshTime = millis();
  }
}


void drawOLED() {
  u8g2.clearBuffer(); // clear the internal memory
  u8g2.setFont(u8g2_font_profont22_mn); // choose a suitable font

  u8g2.setCursor(0, 15);
  u8g2.print(sRad, 1);
  u8g2.setCursor(0, 32);
  u8g2.print(sAmb, 1);

  u8g2.setCursor(82, 15);
  u8g2.print(deltaT);
  u8g2.setCursor(82, 32);
  u8g2.print(String(pwm));
  u8g2.sendBuffer();
}

// Set variables based on input from Serial interface
void parseSerial() {
  byte msg = Serial.read();
  switch (msg) {
    case 'r': // r for readCount
      readCount = Serial.parseInt();
      break;
    case 't': // t for top
      s_max = Serial.parseInt();
      break;
    case 'l': // l for lift
      s_min = Serial.parseInt();
      break;
    case 's': // s for slope
      s_slope = Serial.parseFloat();
      break;
    case 'a': // a for attack
      s_attack = Serial.parseFloat();
      break;
    case 'f': // f for forced value
      static_pwm = Serial.parseInt();
      break;
    case 'x': // x for multiple values from python gui
      String str = Serial.readString();
      int n = str.length();
      char buff[n + 1];
      strcpy(buff, str.c_str());
      //Serial.println(buff);
      int temp1;
      int temp2;
      sscanf(buff, "%d %d %d %d", &s_min, &s_max, &temp1, &temp2); //sending Data: x15 89 -49 573
      s_slope = (float(temp1) / 100.0);
      s_attack = (float(temp2) / 100.0);
      break;
    default:
      break;
  }
}

// read Temperatures based on NTC Resistors
// https://www.electronics-tutorials.ws/io/thermistors.html
float readNTCTemp(int analogPin, int BValue) {
  float sum = 0;
  VCC = 5.0; // Reference Voltage
  for (int i = 0; i < readCount; i++) {
    VRT = analogRead(analogPin);      //Acquisition analog value of VRT
    VRT = (VCC / 1023) * VRT;         //Conversion to voltage
    VR = VCC - VRT;
    RT = VRT / (VR / R);              //Resistance of RT
    ln = log(RT / R);
    TX = (1 / ((ln / BValue) + (1 / T0))); //Temperature from thermistor
    TX = TX - 273.15;                 //Conversion to Celsius
    sum += TX;
  }
  return sum / readCount;
}

// Calculate target PWM cycle based on Sigmoid function
byte getTargetPWM(float deltaTemp) {
  byte targetPWM = s_max * ((1 - (float(s_min) / float(s_max))) / (1 + pow(2.718, (s_slope * deltaTemp + s_attack))) + float(s_min) / float(s_max));
  return targetPWM;
}

// Set PWM duty cycle 0-100%
// PWM Controll - https://create.arduino.cc/projecthub/tylerpeppy/25-khz-4-pin-pwm-fan-control-with-arduino-uno-3005a1
void setPwmDuty(byte duty) {
  OCR1A = (word) (duty * TCNT1_TOP) / 100;
}
