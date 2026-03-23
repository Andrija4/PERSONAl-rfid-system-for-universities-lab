#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 5
#define RST_PIN 22
#define LED_GREEN 2
#define LED_RED 4
//#define BUZZER 15

const char* ssid = "raflab";
const char* password = "rafpassword";
const char* apiUrl = "http://192.168.1.XXX:8000/functions/v1/rfid-api/check"; //Change to your PC's local IP

MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(115200);

  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  //pinMode(BUZZER, OUTPUT);

  SPI.begin();
  rfid.PCD_Init();

  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.println("RFID Access Control System Ready");
  Serial.println("Scan your card...");
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  String rfidNumber = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    rfidNumber += String(rfid.uid.uidByte[i], HEX);
  }
  rfidNumber.toUpperCase();

  Serial.println("Card detected: " + rfidNumber);

  checkRFIDAccess(rfidNumber);

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  delay(2000);
}

void checkRFIDAccess(String rfidNumber) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    http.begin(apiUrl);
    http.addHeader("Content-Type", "application/json");

    String jsonPayload = "{\"rfid_number\":\"" + rfidNumber + "\"}";

    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Response: " + response);

      DynamicJsonDocument doc(1024);
      DeserializationError error = deserializeJson(doc, response);

      if (!error) {
        bool accessGranted = doc["access_granted"];

        if (accessGranted) {
          String userName = doc["user"]["name"];
          Serial.println("Access GRANTED for: " + userName);

          digitalWrite(LED_GREEN, HIGH);
          digitalWrite(LED_RED, LOW);
          //digitalWrite(BUZZER, HIGH);
          delay(3000);
          //digitalWrite(BUZZER, LOW);
          digitalWrite(LED_GREEN, LOW);

        } else {
          Serial.println("Access DENIED");

          digitalWrite(LED_RED, HIGH);
          digitalWrite(LED_GREEN, LOW);
          //digitalWrite(BUZZER, HIGH);
          delay(1000);
          //digitalWrite(BUZZER, LOW);
          digitalWrite(LED_RED, LOW);
        }
      }
    } else {
      Serial.println("Error: " + String(httpResponseCode));
      digitalWrite(LED_RED, HIGH);
      delay(500);
      digitalWrite(LED_RED, LOW);
    }

    http.end();
  } else {
    Serial.println("WiFi disconnected!");
  }
}