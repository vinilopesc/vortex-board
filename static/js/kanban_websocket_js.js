// static/js/kanban-websocket.js
// Sistema de WebSocket para atualizações em tempo real do Kanban

let kanbanSocket = null;
let reconnectInterval = null;
let heartbeatInterval = null;
let onlineUsers = new Set();

/**
 * Inicializa conexão WebSocket para o board
 */
function initKanbanWebSocket() {
    // Verificar se as variáveis necessárias estão definidas
    if (typeof BOARD_ID === 'undefined' || typeof WS_GROUP === 'undefined') {
        console.error('❌ Variáveis WebSocket não definidas');
        return;
    }
    
    console.log('🔌 Iniciando conexão WebSocket para board:', BOARD_ID);
    
    // Construir URL do WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/board/${BOARD_ID}/`;
    
    try {
        kanbanSocket = new WebSocket(wsUrl);
        setupWebSocketEvents();
    } catch (error) {
        console.error('❌ Erro ao criar WebSocket:', error);
        fallbackToPolling();
    }
}

/**
 * Configura event listeners do WebSocket
 */
function setupWebSocketEvents() {
    kanbanSocket.onopen = function(e) {
        console.log('✅ WebSocket conectado');
        showConnectionStatus('connected');
        startHeartbeat();
        
        // Limpar tentativas de reconexão
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    kanbanSocket.onmessage = function(e) {
        try {
            const data = JSON.parse(e.data);
            handleWebSocketMessage(data);
        } catch (error) {
            console.error('❌ Erro ao processar mensagem WebSocket:', error);
        }
    };
    
    kanbanSocket.onclose = function(e) {
        console.log('🔌 WebSocket desconectado. Código:', e.code);
        showConnectionStatus('disconnected');
        stopHeartbeat();
        
        // Tentar reconectar após delay
        if (!reconnectInterval) {
            scheduleReconnect();
        }
    };
    
    kanbanSocket.onerror = function(e) {
        console.error('❌ Erro no WebSocket:', e);
        showConnectionStatus('error');
    };
}

/**
 * Processa mensagens recebidas via WebSocket
 */
function handleWebSocketMessage(data) {
    console.log('📨 Mensagem WebSocket recebida:', data.type);
    
    switch (data.type) {
        case 'item_moved':
            handleItemMoved(data.message);
            break;
            
        case 'item_created':
            handleItemCreated(data.message);
            break;
            
        case 'comment_added':
            handleCommentAdded(data.message);
            break;
            
        case 'user_joined':
            handleUserJoined(data.message);
            break;
            
        case 'user_left':
            handleUserLeft(data.message);
            break;
            
        case 'user_typing':
            handleUserTyping(data.message);
            break;
            
        case 'board_refresh':
            handleBoardRefresh(data.message);
            break;
            
        case 'pong':
            // Resposta do heartbeat - conexão ativa
            break;
            
        default:
            console.log('🤷 Tipo de mensagem desconhecido:', data.type);
    }
}

/**
 * Lida com movimentação de item por outro usuário
 */
function handleItemMoved(message) {
    const notification = `
        <strong>${message.usuario}</strong> moveu 
        <em>${message.item_titulo}</em> 
        para <strong>${message.nova_coluna}</strong>
    `;
    
    showToast(notification, 'info', 3000);
    
    // TODO: Atualizar posição do item no DOM se necessário
    // (evitar conflitos com movimentações locais)
}

/**
 * Lida com criação de novo item
 */
function handleItemCreated(message) {
    const notification = `
        <strong>${message.usuario}</strong> criou 
        ${message.item_type === 'bug' ? '🐛' : '✨'} 
        <em>${message.item_titulo}</em>
    `;
    
    showToast(notification, 'success', 4000);
    
    // TODO: Adicionar item ao DOM ou mostrar botão de refresh
}

/**
 * Lida com novo comentário
 */
function handleCommentAdded(message) {
    const notification = `
        <strong>${message.usuario}</strong> comentou em 
        <em>${message.item_titulo}</em>
    `;
    
    showToast(notification, 'info', 3000);
    
    // TODO: Atualizar contador de comentários no item
}

/**
 * Lida com usuário entrando no board
 */
function handleUserJoined(message) {
    onlineUsers.add(message.user_id);
    updateOnlineUsersDisplay();
    
    const notification = `${message.usuario} entrou no board`;
    showToast(notification, 'info', 2000);
}

/**
 * Lida com usuário saindo do board
 */
function handleUserLeft(message) {
    onlineUsers.delete(message.user_id);
    updateOnlineUsersDisplay();
    
    const notification = `${message.usuario} saiu do board`;
    showToast(notification, 'info', 2000);
}

/**
 * Lida com indicação de usuário digitando
 */
function handleUserTyping(message) {
    // TODO: Mostrar indicador de "usuário digitando" próximo ao item
    console.log(`👤 ${message.usuario} está digitando...`);
}

/**
 * Força refresh do board por mudança importante
 */
function handleBoardRefresh(message) {
    showToast('Board atualizado por outro usuário. Recarregando...', 'info', 2000);
    
    setTimeout(() => {
        window.location.reload();
    }, 2000);
}

/**
 * Atualiza display de usuários online
 */
function updateOnlineUsersDisplay() {
    const onlineCountElement = document.getElementById('online-count');
    if (onlineCountElement) {
        onlineCountElement.textContent = onlineUsers.size;
    }
    
    // TODO: Mostrar lista de usuários online em tooltip ou dropdown
}

/**
 * Mostra status da conexão
 */
function showConnectionStatus(status) {
    const statusColors = {
        connected: 'bg-green-500',
        disconnected: 'bg-red-500',
        error: 'bg-yellow-500'
    };
    
    const statusMessages = {
        connected: 'Conectado',
        disconnected: 'Desconectado',
        error: 'Erro de conexão'
    };
    
    // Atualizar indicador visual se existir
    const indicator = document.querySelector('.user-online');
    if (indicator) {
        indicator.className = `user-online ${statusColors[status] || 'bg-gray-500'}`;
        indicator.title = statusMessages[status] || 'Status desconhecido';
    }
}

/**
 * Inicia heartbeat para manter conexão ativa
 */
function startHeartbeat() {
    heartbeatInterval = setInterval(() => {
        if (kanbanSocket && kanbanSocket.readyState === WebSocket.OPEN) {
            kanbanSocket.send(JSON.stringify({
                type: 'ping',
                timestamp: new Date().toISOString()
            }));
        }
    }, 30000); // Ping a cada 30 segundos
}

/**
 * Para heartbeat
 */
function stopHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
}

/**
 * Agenda tentativa de reconexão
 */
function scheduleReconnect() {
    const delay = 5000; // 5 segundos
    
    console.log(`🔄 Tentando reconectar em ${delay/1000}s...`);
    
    reconnectInterval = setTimeout(() => {
        console.log('🔄 Tentando reconectar...');
        initKanbanWebSocket();
    }, delay);
}

/**
 * Envia mensagem via WebSocket
 */
function sendWebSocketMessage(type, data = {}) {
    if (kanbanSocket && kanbanSocket.readyState === WebSocket.OPEN) {
        const message = {
            type: type,
            ...data,
            timestamp: new Date().toISOString()
        };
        
        kanbanSocket.send(JSON.stringify(message));
        return true;
    } else {
        console.warn('⚠️ WebSocket não conectado. Não foi possível enviar:', type);
        return false;
    }
}

/**
 * Notifica que usuário está digitando comentário
 */
function notifyTyping(itemId, itemType, isTyping = true) {
    sendWebSocketMessage('typing_comment', {
        item_id: itemId,
        item_type: itemType,
        is_typing: isTyping
    });
}

/**
 * Fallback para polling quando WebSocket não funciona
 */
function fallbackToPolling() {
    console.log('📡 WebSocket não disponível. Usando polling como fallback...');
    
    // TODO: Implementar polling simples para atualizações
    // setInterval(() => {
    //     checkForUpdates();
    // }, 30000);
    
    showConnectionStatus('disconnected');
}

/**
 * Limpa conexões ao sair da página
 */
function cleanupWebSocket() {
    if (kanbanSocket) {
        kanbanSocket.close();
        kanbanSocket = null;
    }
    
    if (reconnectInterval) {
        clearInterval(reconnectInterval);
        reconnectInterval = null;
    }
    
    stopHeartbeat();
}

// Event listeners globais
window.addEventListener('beforeunload', cleanupWebSocket);
window.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Página ficou invisível - pausar heartbeat
        stopHeartbeat();
    } else {
        // Página ficou visível - retomar heartbeat
        if (kanbanSocket && kanbanSocket.readyState === WebSocket.OPEN) {
            startHeartbeat();
        }
    }
});

// Função global para inicialização
window.initKanbanWebSocket = initKanbanWebSocket;
window.sendWebSocketMessage = sendWebSocketMessage;
window.notifyTyping = notifyTyping;

// Debug: Log quando arquivo é carregado
console.log('📁 kanban-websocket.js carregado');