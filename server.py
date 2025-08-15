import socket
import threading
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()
HOST = os.environ["HOST"]
PORT = int(os.environ["PORT"])
SERVER_TICK_RATE = 60 
WIDTH, HEIGHT = 800, 600
BLOCK_WIDTH, BLOCK_HEIGHT = 15, 100
BALL_RADIUS = 7
WINNING_SCORE = 5

clients = {}
games = {}
lobbies = {}
next_player_id = 0
lock = threading.Lock()

class Game:
    def __init__(self, game_id, player1_conn):
        self.id = game_id
        self.players = [player1_conn, None]
        self.score = [0, 0]
        self.ball_pos = [WIDTH / 2, HEIGHT / 2]
        self.ball_vel = [5, 5] 
        self.player_y = [HEIGHT / 2 - BLOCK_HEIGHT / 2, HEIGHT / 2 - BLOCK_HEIGHT / 2]
        self.ready = False
        self.game_thread = threading.Thread(target=self.game_loop, daemon=True)

    def add_player(self, player2_conn):
        if not self.players[1]:
            self.players[1] = player2_conn
            self.ready = True
            self.game_thread.start()
            return True
        return False

    def reset_ball(self, direction=1):
        self.ball_pos = [WIDTH / 2, HEIGHT / 2]
        self.ball_vel = [5 * direction, 5]

    def update(self):
        
        self.ball_pos[0] += self.ball_vel[0]
        self.ball_pos[1] += self.ball_vel[1]

        
        if self.ball_pos[1] - BALL_RADIUS <= 0 or self.ball_pos[1] + BALL_RADIUS >= HEIGHT:
            self.ball_vel[1] *= -1

        
        p1_y = self.player_y[0]
        if self.ball_vel[0] < 0 and \
           10 <= self.ball_pos[0] - BALL_RADIUS <= 10 + BLOCK_WIDTH and \
           p1_y <= self.ball_pos[1] <= p1_y + BLOCK_HEIGHT:
            self.ball_vel[0] *= -1.1 
            self.ball_vel[1] += (self.ball_pos[1] - (p1_y + BLOCK_HEIGHT/2)) / 20

        
        p2_y = self.player_y[1]
        if self.ball_vel[0] > 0 and \
           WIDTH - 10 - BLOCK_WIDTH <= self.ball_pos[0] + BALL_RADIUS <= WIDTH - 10 and \
           p2_y <= self.ball_pos[1] <= p2_y + BLOCK_HEIGHT:
            self.ball_vel[0] *= -1.1 
            self.ball_vel[1] += (self.ball_pos[1] - (p2_y + BLOCK_HEIGHT/2)) / 20


        
        if self.ball_pos[0] < 0:
            self.score[1] += 1
            self.reset_ball(1)
        elif self.ball_pos[0] > WIDTH:
            self.score[0] += 1
            self.reset_ball(-1)

    def get_state(self):
        return {
            "type": "GAME_STATE",
            "ball": self.ball_pos,
            "player1_y": self.player_y[0],
            "player2_y": self.player_y[1],
            "score": self.score
        }

    def game_loop(self):
        
        send_to_player(self.players[0], {"type": "GAME_START", "player_id": 0})
        send_to_player(self.players[1], {"type": "GAME_START", "player_id": 1})
        
        while True:
            if not self.ready:
                break
                
            self.update()
            
            
            if self.score[0] >= WINNING_SCORE or self.score[1] >= WINNING_SCORE:
                winner = 0 if self.score[0] >= WINNING_SCORE else 1
                game_over_msg = {"type": "GAME_OVER", "winner": winner}
                self.broadcast(game_over_msg)
                break

            
            self.broadcast(self.get_state())
            time.sleep(1 / SERVER_TICK_RATE)
        
        
        with lock:
            if self.id in games:
                del games[self.id]
        print(f"[GAME] Partida '{self.id}' finalizada.")


    def broadcast(self, message):
        for p_conn in self.players:
            if p_conn:
                send_to_player(p_conn, message)

def send_to_player(connectionSocket, data):
    try:
        message = json.dumps(data) + '\n'
        connectionSocket.sendall(message.encode('utf-8'))
    except (BrokenPipeError, ConnectionResetError):
        print("[NETWORK] Cliente desconectado abruptamente.")
        
        pass

def handle_client(connectionSocket, addr):
    print(f"[NETWORK] Nova conexão de {addr}")
    global next_player_id
    player_id = -1
    my_game_id = None

    try:
        for line in connectionSocket.makefile('r'):
            try:
                data = json.loads(line)
                command = data.get("command")

                with lock:
                    if command == "CREATE_GAME":
                        game_id = data.get("game_id")
                        password = data.get("password")
                        print(f"[LOBBY] partida {game_id} criar com a senha {password}")
                        if game_id in games or game_id in lobbies:
                            send_to_player(connectionSocket, {"status": "ERROR", "message": "Este nome de partida já existe."})
                        else:
                            lobbies[game_id] = {"password": password, "players": [connectionSocket]}
                            my_game_id = game_id
                            send_to_player(connectionSocket, {"status": "SUCCESS", "message": f"Partida '{game_id}' criada. Aguardando outro jogador."})
                            print(f"[LOBBY] Partida '{game_id}' criada.")

                    elif command == "JOIN_GAME":
                        game_id = data.get("game_id")
                        password = data.get("password")
                        if game_id in lobbies and len(lobbies[game_id]["players"]) == 1:
                            lobby = lobbies[game_id]
                            if lobby["password"] and lobby["password"] != password:
                                send_to_player(connectionSocket, {"status": "ERROR", "message": "Senha incorreta."})
                            else:
                                player1_conn = lobby["players"][0]
                                new_game = Game(game_id, player1_conn)
                                new_game.add_player(connectionSocket)
                                games[game_id] = new_game
                                my_game_id = game_id
                                del lobbies[game_id]
                                send_to_player(connectionSocket, {"status": "SUCCESS", "message": f"Entrou na partida '{game_id}'. O jogo vai começar!"})
                                print(f"[GAME] Partida '{game_id}' iniciada.")
                        else:
                            send_to_player(connectionSocket, {"status": "ERROR", "message": "Partida não encontrada ou já está cheia."})
                    
                    elif command == "UPDATE_BLOCK":
                        game_id = my_game_id
                        player_index = games[game_id].players.index(connectionSocket)
                        if game_id in games:
                            games[game_id].player_y[player_index] = data.get("y")

                    elif command == "FINISH_CONNECTION":
                        break

            except json.JSONDecodeError:
                print(f"[ERROR] Mensagem JSON mal formada de {addr}")
            except Exception as e:
                print(f"[ERROR] Erro inesperado ao processar comando: {e}")


    finally:
        with lock:
            if my_game_id:
                
                if my_game_id in lobbies:
                    del lobbies[my_game_id]
                
                elif my_game_id in games:
                    games[my_game_id].ready = False 
                    
        print(f"[NETWORK] Conexão com {addr} fechada.")
        connectionSocket.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[INFO] Servidor escutando em {HOST}:{PORT}")

    while True:
        connectionSocket, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(connectionSocket, addr))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    main()