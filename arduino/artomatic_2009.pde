#define SOLENOID_PIN 8
#define LED_PIN 13
#define SENSOR_PIN 0
#define BAUD_RATE 9600
#define BELL_CHAR '#'
#define STARTUP_DELAY_IN_SECONDS 80

int lastRing = 0;
int minimum_observed = 999;
int maximum_observed = 0;
bool last_ring_state = false;
bool past_startup_delay = false;

float load;

void setup()
{
  load = 0;
  
  pinMode(LED_PIN, OUTPUT);
  pinMode(SOLENOID_PIN, OUTPUT);
  pinMode(SENSOR_PIN, INPUT);
  
  digitalWrite(LED_PIN, LOW);
  digitalWrite(SOLENOID_PIN, LOW);

  Serial.begin(BAUD_RATE);
}

bool BellIsRinging()
{
  int val = analogRead(SENSOR_PIN);    // read the value from the sensor
  minimum_observed = min(minimum_observed, val);
  maximum_observed = max(maximum_observed, val);

  if(val > ((minimum_observed + maximum_observed)/2))
  {
    // digitalWrite(LED_PIN, HIGH);
    return true;
  }
  else
  {
    // digitalWrite(LED_PIN, LOW);
    return false;
  }
}

void RingBell()
{
  // assumes one ring every 100 ms max -- this is 50% solenoid utilization
  if(load<1.0)
  {
    digitalWrite(SOLENOID_PIN, HIGH);
    delay(20); // waits for a brief moment to properly energize the solenoid
    digitalWrite(SOLENOID_PIN, LOW);

    // prevent looping of strikes (?)
    delay(30);

    last_ring_state = true;

    load = (0.9*load) + (0.1 * (100 / (millis() - lastRing)));
    lastRing = millis();
  }
}

void SendBellRing()
{
  Serial.println(BELL_CHAR);
  
  digitalWrite(LED_PIN, HIGH);
  delay(100);
  digitalWrite(LED_PIN, LOW);
}

void loop()
{
  // do it this way in case millis() loops around
  if (millis()>=(STARTUP_DELAY_IN_SECONDS*1000))
  {
    past_startup_delay = true;
  }
  
  if (Serial.available() > 0) 
  {
    int incoming = Serial.read();    
    if ((char(incoming)==BELL_CHAR) && past_startup_delay)
    {
      RingBell();
    }
  }

  bool bell_is_ringing = BellIsRinging();
  if(bell_is_ringing && !last_ring_state)
  {
    SendBellRing();
  }
  last_ring_state = bell_is_ringing;
}
