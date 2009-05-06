# Echo server program
try:
    import socket
except Exception, e:
    import _socket as socket
import time
import settings

class BellServer(object):
    """
    Handles listening for and responding to network and serial events within the Ring For Service project    
    """

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
        
    def close(self):
        """
        Close socket to free it up for server restart or other uses.
        """
        self.socket.close()
    
    def bell_strike_detected(self):
        """
        Checks the serial connection for notice of a bell strike from the Arduino.
        """
        # TODO: everything
        return False
        
    def transmit_bell_strike(self):
        """
        Send a bell strike notification across the network
        """
        for recipient in self.RECIPIENTS:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((recipient, self.PORT))
            s.send('[X]')
            data = s.recv(1024)
            s.close()
            print 'Received', repr(data)
        
    def strike_bell(self):
        """
        Send a bell strike notification to the Arduino over the serial link
        """
        pass
        
    def loop(self):
        """
        Main server loop
        """

        self.socket.listen(1)
        while 1:
            # check serial input for bell strike notification
            if self.bell_strike_detected():
                self.send_bell()

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
                    self.strike_bell()
                    conn.send(data.upper())


if __name__ == '__main__':
    B = BellServer()
    try:
        B.loop()
    finally:
        # shutdown socket
        B.close()