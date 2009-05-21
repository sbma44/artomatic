# Echo server program
try:
    import socket
except Exception, e:
    import _socket as socket
import os
import serial
import time
import settings
import SocketServer


def log(message):
    line = "%f - %s\n" % (time.time(), message)
    
    filename = getattr(settings,'LOG',False)
    if filename:
        try:
            f = open(filename, 'a')
            f.write(line)
            f.close()
        except Exception, e:
            filename = False
    
    if not filename:
        print line

class SerialHolder(object):
    SERIAL_BELL_STRIKE_SIGNAL = '#'

    def __init__(self):
        super(SerialHolder, self).__init__()

        # create a serial connection
        log("Establishing serial connection")
        self.serial_connection = serial.Serial(settings.SERIAL_PORT, settings.BAUD_RATE, timeout=0)

        # clear serial backlog
        waiting = self.serial_connection.inWaiting()
        self.serial_connection.read(waiting)
      
    def strike_bell(self):
        self.serial_connection.write(self.SERIAL_BELL_STRIKE_SIGNAL)
        log("Struck bell")        
  
    def bell_strike_detected(self):
        """
        Checks the serial connection for notice of a bell strike from the Arduino.
        """
        char = ''
        try:
            waiting = self.serial_connection.inWaiting()
            if waiting>0:
                char = self.serial_connection.read(waiting)    
        except Exception, e:
            pass

        if len(char.strip())>0:
            log("Detected serial communication - %s" % (char))
            return char.count(self.SERIAL_BELL_STRIKE_SIGNAL)

        return False
    
    def close(self):
        self.serial_connection.close()
                


class SocketServerWrapper(SocketServer.TCPServer):
    """docstring for SocketServerWrapper"""
    def __init__(self, *args):
        log("Starting server")
        self.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self,*args)

        

class BellServer(SocketServer.StreamRequestHandler):

    NETWORK_BELL_STRIKE_SIGNAL = 'DING'
    NETWORK_BELL_STRIKE_CONFIRMATION = 'DONG'
            
    def strike_bell(self):
        """
        Send a bell strike notification to the Arduino over the serial link
        """
        log("Striking bell")
        global serialholder
        if serialholder is not None:
            serialholder.strike_bell()

    def handle(self):
        data = self.rfile.readline().strip()
        log("Received data %s" % data)
        if data==self.NETWORK_BELL_STRIKE_SIGNAL:
            self.strike_bell()                    
            self.wfile.write(self.NETWORK_BELL_STRIKE_CONFIRMATION)
        
        
class BellClient(object):
    """
    Monitors the serial port for strikes and sends network messages when they're found
    """

    def __init__(self):
        log("Starting client")
        super(BellClient, self).__init__()
     
        self.RECIPIENTS = settings.RECIPIENTS
        self.PORT = settings.PORT

        self.NETWORK_BELL_STRIKE_SIGNAL = 'DING'
        self.NETWORK_BELL_STRIKE_CONFIRMATION = 'DONG'
            
    def bell_strike_detected(self):
        """
        Checks the serial connection for notice of a bell strike from the Arduino.
        """
        global serialholder
        if serialholder is not None:
            return serialholder.bell_strike_detected()

        return False

    def transmit_bell_strike(self):
        """
        Send a bell strike notification across the network
        """
        log("Transmitting bell strike to %d recipient(s)" % len(self.RECIPIENTS))

        for recipient in self.RECIPIENTS:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)       
            s.settimeout(1)
            
            try:                
                s.connect((recipient, self.PORT))
                s.send(self.NETWORK_BELL_STRIKE_SIGNAL + "\n")            

                data = ''
                try:
                    data = s.recv(1024)
                except Exception, e:
                    pass

                s.close()
            
                if data==self.NETWORK_BELL_STRIKE_CONFIRMATION:
                    log("Successfully sent bell strike to %s" % recipient)
                else:
                    log("Unable to confirm bell strike to %s (network timeout?)" % recipient)

            except Exception, e:
                log("Tried to send bell strike to %s but failed" % recipient)

    
    def listen(self):
        while True:
            # check serial input for bell strike notification
            strikes_in_waiting = self.bell_strike_detected()
            if strikes_in_waiting is not False:
                log("Heard at least one strike")
                for i in range(0, strikes_in_waiting):
                    self.transmit_bell_strike()
            time.sleep(0.01)

    def close(self):
        global serialholder
        if serialholder is not None:
            serialholder.close()


global serialholder
serialholder = SerialHolder()

if __name__ == '__main__':
    
    if os.fork():
        server = SocketServerWrapper( (settings.HOST, settings.PORT), BellServer)
        server.serve_forever()
    else:
        client = BellClient()
        try:         
            client.listen()
        finally:
            client.close()