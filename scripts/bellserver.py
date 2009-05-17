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

class BellServer(SocketServer.StreamRequestHandler):
    """
    Handles listening for and responding to network and serial events within the Ring For Service project    
    """

    NETWORK_BELL_STRIKE_SIGNAL = 'DING'
    NETWORK_BELL_STRIKE_CONFIRMATION = 'DONG'
    SERIAL_BELL_STRIKE_SIGNAL = '#'

    def __init__(self):
        super(BellServer, self).__init__()

        self.log("Starting up")

        # set settings
        self.HOST = settings.HOST
        self.RECIPIENTS = settings.RECIPIENTS
        self.PORT = settings.PORT        

        # create a nonblocking socket to handle server responsibilities
        self.log("Creating server socket")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)        
        self.socket.setblocking(0)
        self.socket.settimeout(0)
        self.socket.bind((self.HOST, self.PORT))
        self.socket.listen(1)                
         
        # create a serial connection
        self.log("Establishing serial connection")
        self.serial_connection = serial.Serial(settings.SERIAL_PORT, settings.BAUD_RATE, timeout=0)
        # clear serial backlog
        waiting = self.serial_connection.inWaiting()
        self.serial_connection.read(waiting)

        # create another socket to send communication to each recipient
        self.log("Creating outbound sockets")
        self.outbound_sockets = {}
        self.setup_outbound_sockets()

    def handle(self):
        print self.rfile.readline().strip()        

    def log(self, message):
        print "%f - %s" % (time.time(), message)
        
    def setup_outbound_sockets(self):
        
        # try to close any open sockets
        for recipient in self.outbound_sockets:
            try:
                self.outbound_sockets[recipient].close()
            except:
                pass
        
        # create connections
        for recipient in settings.RECIPIENTS:
            socket_creation_successful = False

            while not socket_creation_successful:
                # s = self._open_xmit_socket(recipient)
                try:
                    s = self._open_xmit_socket(recipient)
                except socket.error:
                    self.log("Failed to establish connection to %s" % recipient)                    
                    socket_creation_successful = False
                    time.sleep(10)
                else:
                    socket_creation_successful = True
                
                if socket_creation_successful:
                    self.log("Successfully created connection to %s" % recipient)
                    self.outbound_sockets[recipient] = s    
                    break
    
    def _open_xmit_socket(self, recipient):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)       
        s.connect((recipient, self.PORT))
        return s
    
    def reset_sockets(self, sockets):
        """
        Reset the passed sockets. Takes a dict in the form sockets[HOST] = SOCKET
        """
        for s in sockets:
            try:
                sockets[s].close()
            except:
                pass
        
        for recipient in sockets:
            socket_creation_successful = False

            while not socket_creation_successful:
                try:
                    s = self._open_xmit_socket(recipient)
                except socket.error:
                    self.log("Failed to re-establish connection to %s" % recipient)
                    socket_creation_successful = False
                else:
                    socket_creation_successful = True

                if socket_creation_successful:
                    self.outbound_sockets[recipient] = s    
                    break
        
        
    
    def close(self):
        """
        Close socket to free it up for server restart or other uses.
        """
        self.socket.close()
        self.serial_connection.close()
        
        for s in self.outbound_sockets:
            self.outbound_sockets[s].close()
    
    def bell_strike_detected(self):
        """
        Checks the serial connection for notice of a bell strike from the Arduino.
        """
        # waiting = self.serial_connection.inWaiting()
        char = ''
        try:
            waiting = self.serial_connection.inWaiting()
            if waiting>0:
                char = self.serial_connection.read(waiting)    
        except Exception, e:
            pass
            
        if len(char.strip())>0:
            self.log("Detected serial communication - %s" % (char))
            return char.count(self.SERIAL_BELL_STRIKE_SIGNAL)
        
        return False
        
    def transmit_bell_strike(self):
        """
        Send a bell strike notification across the network
        """        
        failed_sockets = {}
        for s in self.outbound_sockets:            
            data = None
            try:                
                self.outbound_sockets[s].send(self.NETWORK_BELL_STRIKE_SIGNAL + "\n")
                data = self.outbound_sockets[s].recv(1024)
            except:
                failed_sockets[s] = self.outbound_sockets[s]

            if data==self.NETWORK_BELL_STRIKE_CONFIRMATION:
                self.log("Successfully sent bell strike")
                
        self.reset_sockets(failed_sockets)
        
    def strike_bell(self):
        """
        Send a bell strike notification to the Arduino over the serial link
        """
        self.serial_connection.write(self.SERIAL_BELL_STRIKE_SIGNAL)
        self.log("Struck bell")
        
    def loop(self):
        """
        Main server loop
        """
        while 1:
            # check serial input for bell strike notification
            strikes_in_waiting = self.bell_strike_detected()
            if strikes_in_waiting is not False:
                for i in range(0, strikes_in_waiting):
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
                    print "loop"
                    data = False
                    try:
                        self.log("Trying to read data from connection...")
                        data = conn.recv(1024)
                        self.log("Finished reading data")
                    except Exception, e:
                        print str(e)

                    if not data: break

                    if data==self.NETWORK_BELL_STRIKE_SIGNAL:
                        self.strike_bell()                    
                        conn.send(self.NETWORK_BELL_STRIKE_CONFIRMATION)
            
            time.sleep(0.01)


if __name__ == '__main__':

    # record pid
    pidfile = open('%s/bellserver.pid' % os.path.abspath(os.path.dirname(__file__)),'w')
    pidfile.write(str(os.getpid()))
    pidfile.close()

    B = BellServer()
    try:
        B.loop()
    finally:
        # shutdown socket
        B.close()        
        os.unlink('%s/bellserver.pid' % os.path.abspath(os.path.dirname(__file__)))