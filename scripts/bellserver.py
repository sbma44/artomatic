# Echo server program
try:
    import socket
except Exception, e:
    import _socket as socket
import serial
import time
import settings

class BellServer(object):
    """
    Handles listening for and responding to network and serial events within the Ring For Service project    
    """

    NETWORK_BELL_STRIKE_SIGNAL = 'DING'
    NETWORK_BELL_STRIKE_CONFIRMATION = 'DONG'
    SERIAL_BELL_STRIKE_SIGNAL = '#'

    def __init__(self):
        super(BellServer, self).__init__()

        self.HOST = settings.HOST
        self.RECIPIENTS = settings.RECIPIENTS
        self.PORT = settings.PORT

        # create a nonblocking socket to handle server responsibilities
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(0)
        s.bind((self.HOST, self.PORT))
        self.socket = s
        
        # create a serial connection
        self.serial_connection = serial.Serial(settings.SERIAL_PORT, settings.BAUD_RATE, timeout=0)
        

    def log(self, message):
        print "%f - %s" % (time.time(), message)
        
    
    def close(self):
        """
        Close socket to free it up for server restart or other uses.
        """
        self.socket.close()
        self.serial_connectsion.close()
    
    def bell_strike_detected(self):
        """
        Checks the serial connection for notice of a bell strike from the Arduino.
        """
        if self.serial_connection.inWaiting()>0:
            return self.serial_connection.read()==self.SERIAL_BELL_STRIKE_SIGNAL
        return False
        
    def transmit_bell_strike(self):
        """
        Send a bell strike notification across the network
        """
        for recipient in self.RECIPIENTS:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((recipient, self.PORT))
            s.send(self.NETWORK_BELL_STRIKE_SIGNAL)
            data = s.recv(1024)
            s.close()
            if data==self.NETWORK_BELL_STRIKE_CONFIRMATION:
                print 'bell successfully struck'
            self.log("Sent bell strike")
        
    def strike_bell(self):
        """
        Send a bell strike notification to the Arduino over the serial link
        """
        self.serial_connection.write(SERIAL_BELL_STRIKE_SIGNAL)
        self.log("Struck bell")
        print 'DING!'        
        
    def loop(self):
        """
        Main server loop
        """

        self.socket.listen(1)
        while 1:
            # check serial input for bell strike notification
            while self.bell_strike_detected():
                self.transmit_bell_strike()

            # listen for incoming network data signalling bell strikes (in a non-blocking-compatible manner)
            data_received = False
            try:
                conn, addr = self.socket.accept()
                data_received = True
            except Exception, e:
                data_received = False
                
            if data_received:
                print 'Connected by', addr
                while 1:
                    data = False
                    try:
                        data = conn.recv(1024)
                    except Exception, e:
                        pass

                    if not data: break

                    # TODO: replace echo with write to serial output to initiate bell strike
                    if data==self.NETWORK_BELL_STRIKE_SIGNAL:
                        self.strike_bell()                    
                        conn.send(self.NETWORK_BELL_STRIKE_CONFIRMATION)
            
            time.sleep(0.01)


if __name__ == '__main__':
    B = BellServer()
    try:
        B.loop()
    finally:
        # shutdown socket
        B.close()