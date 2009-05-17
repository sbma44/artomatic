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
    print "%f - %s" % (time.time(), message)

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
                
                
class adsas(object):
    """docstring for adsas"""
    def __init__(self, arg):
        super(adsas, self).__init__()
        self.arg = arg
                        

class SocketServerWrapper(SocketServer.TCPServer):
    """docstring for SocketServerWrapper"""
    def __init__(self, *args):
        self.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self,*args)

        

class BellServer(SocketServer.StreamRequestHandler):

    NETWORK_BELL_STRIKE_SIGNAL = 'DING'
    NETWORK_BELL_STRIKE_CONFIRMATION = 'DONG'
    
        
    def strike_bell(self):
        """
        Send a bell strike notification to the Arduino over the serial link
        """
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
    

    
    def __init__(self):
        super(BellClient, self).__init__()
     
        self.RECIPIENTS = settings.RECIPIENTS
        self.PORT = settings.PORT

        self.NETWORK_BELL_STRIKE_SIGNAL = 'DING'
        self.NETWORK_BELL_STRIKE_CONFIRMATION = 'DONG'
     
        # create another socket to send communication to each recipient
        # log("Creating outbound sockets")
        # self.outbound_sockets = {}
        # self.setup_outbound_sockets()
            
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
        # failed_sockets = {}
        # for s in self.outbound_sockets:            
        #     data = None
        #     try:                
        #         self.outbound_sockets[s].send(self.NETWORK_BELL_STRIKE_SIGNAL + "\n")
        #         data = self.outbound_sockets[s].recv(1024)
        #         self.outbound_sockets[s].close()
        #     except:
        #         failed_sockets[s] = self.outbound_sockets[s]            
        #     if data==self.NETWORK_BELL_STRIKE_CONFIRMATION:
        #         log("Successfully sent bell strike")
        # 
        # self.reset_sockets(failed_sockets)
        log("Transmitting bell strike")

        for recipient in self.RECIPIENTS:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)       
            s.settimeout(0.5)
            s.connect((recipient, self.PORT))
            s.send(self.NETWORK_BELL_STRIKE_SIGNAL + "\n")            
            log("Receiving data")
            data = s.recv(1024)
            log("Done receiving data")
            s.close()
            
            if data==self.NETWORK_BELL_STRIKE_CONFIRMATION:
                log("Successfully sent bell strike to %s" % recipient)
            

    def _open_xmit_socket(self, recipient):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)       
        s.connect((recipient, self.PORT))
        return s


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
                    log("Failed to establish connection to %s" % recipient)                    
                    socket_creation_successful = False
                    time.sleep(10)
                else:
                    socket_creation_successful = True

                if socket_creation_successful:
                    log("Successfully created connection to %s" % recipient)
                    self.outbound_sockets[recipient] = s    
                    break

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
                    log("Failed to re-establish connection to %s" % recipient)
                    socket_creation_successful = False
                else:
                    socket_creation_successful = True

                if socket_creation_successful:
                    self.outbound_sockets[recipient] = s    
                    break

    
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

        #for s in self.outbound_sockets:
        #    self.outbound_sockets[s].close()





    
        

        
    # def loop(self):
    #     """
    #     Main server loop
    #     """
    #     while True:
    #         print "loop A"
    #         
    # 
    #         # listen for incoming network data signalling bell strikes (in a non-blocking-compatible manner)
    #         data_received = False
    #         try:
    #             conn, addr = self.socket.accept()
    #             data_received = True
    #         except Exception, e:
    #             data_received = False
    #             
    #         if data_received:
    #             print 'Connected by', addr
    #             while 1:
    #                 print "loop B"
    #                 data = False
    #                 try:
    #                     log("Trying to read data from connection...")
    #                     data = conn.recv(1024)
    #                     log("Finished reading data")
    #                 except Exception, e:
    #                     print str(e)
    # 
    #                 if not data: 
    #                     print "breaking"
    #                     break
    # 
    #                 if data==self.NETWORK_BELL_STRIKE_SIGNAL:
    #                     self.strike_bell()                    
    #                     conn.send(self.NETWORK_BELL_STRIKE_CONFIRMATION)
    #         
    #         time.sleep(0.01)


global serialholder
serialholder = SerialHolder()


if __name__ == '__main__':

    # record pid
    pidfile = open('%s/bellserver.pid' % os.path.abspath(os.path.dirname(__file__)),'w')
    pidfile.write(str(os.getpid()))
    pidfile.close()    
    
    if os.fork():        
        #server = SocketServer.TCPServer( (settings.HOST, settings.PORT), BellServer)
        server = SocketServerWrapper( (settings.HOST, settings.PORT), BellServer)
        server.serve_forever()
    else:
        client = BellClient()
        try:         
            client.listen()
        finally:
            client.close()