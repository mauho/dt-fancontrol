// PWM Controll - https://create.arduino.cc/projecthub/tylerpeppy/25-khz-4-pin-pwm-fan-control-with-arduino-uno-3005a1

#define R 10000   // R = 10KΩ -> voltage divider resistance

// Functions
float readTemp(int analogPin, int BValue);
byte getTargetPWM(float dt);
void setPwmDuty(byte duty);
float readVcc();

// Constants
const byte OC1A_PIN = 9;   // first Fan to controll
//const byte OC1B_PIN = 10;  // second fan to controll
const word PWM_FREQ_HZ = 25000; //Adjust this value to adjust the frequency
const word TCNT1_TOP = 16000000 / (2 * PWM_FREQ_HZ);

// Variables
float RT, VR, ln, TX, T0, VRT, sExp, sRad, sAmb, deltaT, VCC;
float s_max, s_slope, s_attack, s_min; // sigmoid variables
byte pwm;
int readCount, STATIC_PWM;

void setup() {
  // Sensors
  pinMode(1, INPUT); // Sensor water temperature
  pinMode(2, INPUT); // Sensor ambient temperature

  // Default number of readings prior to calculate and send PWM signal and data
  readCount = 727;

  // Default sigmoid parameters - see https://www.geogebra.org/calculator with file in project folder for visualization
  s_max = 90;     // maximum PWM level to be reached 
  s_min = 0;      // minimum PWM level lift in order to prevent fans from stopping (changes with v)
  s_slope = -0.6; // slope -> how big deltaT has to be to reach a cerain pwm level
  s_attack = 5.0; // how far the sigmoid function is shifted to the right

  Serial.begin(57600);
  T0 = 25 + 273.15;  // Temperature T0 from datasheet, conversion from Celsius to kelvin

  // PWM Settings
  pinMode(OC1A_PIN, OUTPUT);
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1  = 0;
  TCCR1A |= (1 << COM1A1) | (1 << WGM11);
  TCCR1B |= (1 << WGM13) | (1 << CS10);
  ICR1 = TCNT1_TOP; // set PWM Frequency
}

void loop() {
  // Check if commands were sent
  parseSerial();  

  // Read temperatures
  sRad = readNTCTemp(1, 3976);
  sAmb = readNTCTemp(2, 3976);

  // Calculate deltaT and set PWM acordingly
  if (STATIC_PWM > 0){
    pwm = STATIC_PWM;
  } else {
    deltaT = (sRad - sAmb);
    pwm = getTargetPWM(deltaT);
  }
 
  setPwmDuty(pwm);

  // Print data to serial
  Serial.print(sRad, 2);
  Serial.print(";");
  Serial.print(sAmb, 2);
  Serial.print(";");
  Serial.print(deltaT);
  Serial.print(";");
  Serial.println(pwm);
}

// Set variables based on input from Serial interface
void parseSerial(){
  if (Serial.available() > 0) {
    byte msg = Serial.read();
    switch (msg) {
      case 'r': // r for readCount
        readCount = Serial.parseInt();
        break;
      case 't': // t for top
        s_max = Serial.parseInt();
        break;
      case 'l': // l for lift
        s_min = Serial.parseFloat();
        break;
      case 's': // s for slope
        s_slope = Serial.parseFloat();
        break;
      case 'a': // a for attack
        s_attack = Serial.parseFloat();
        break;
      case 'f': // f for fixed value
        STATIC_PWM = Serial.parseInt();
      default:
        break;
    }
  }
}

// read Temperatures based on NTC Resistors
// https://www.electronics-tutorials.ws/io/thermistors.html
float readNTCTemp(int analogPin, int BValue) {
  float sum = 0;
  VCC = readVcc();
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

// Read Board VCC based on internal 1.1v reference
// Source https://www.bjoerns-techblog.de/2019/11/spannung-messen-mit-dem-arduino-promini/
float readVcc() {
  long result;                        // Read 1.1V reference against AVcc
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
  delay(3);                           // Wait for Vref to settle
  ADCSRA |= _BV(ADSC);                // Convert
  while (bit_is_set(ADCSRA, ADSC));
  result = ADCL;
  result |= ADCH << 8;
  result = 1126400L / result;         // Back-calculate AVcc in mV
  return float(result) / 1000;        // Return as Volts
}

// Calculate target PWM cycle based on Sigmoid function
byte getTargetPWM(float deltaTemp) {
  byte targetPWM = s_max * ((1 - (s_min / s_max)) / (1 + pow(2.71828, (s_slope * deltaTemp + s_attack))) + (s_min / s_max));
  return targetPWM;
}

// Set PWM duty cycle 0-100%
void setPwmDuty(byte duty) {
  OCR1A = (word) (duty * TCNT1_TOP) / 100;
}
