// static/js/kanban-drag-drop.js
// Sistema de Drag and Drop para o Kanban Board

// Variáveis globais para drag and drop
let draggedElement = null;
let draggedData = null;

/**
 * Inicializa os event listeners de drag and drop
 */
function initializeDragAndDrop() {
    console.log('🎯 Inicializando Drag and Drop...');
    
    // Adicionar eventos a todos os items existentes
    const items = document.querySelectorAll('.kanban-item');
    items.forEach(item => {
        addDragListeners(item);
    });
    
    // Adicionar eventos às colunas
    const colunas = document.querySelectorAll('.kanban-coluna');
    colunas.forEach(coluna => {
        addDropListeners(coluna);
    });
}

/**
 * Adiciona event listeners de drag a um item
 */
function addDragListeners(item) {
    item.addEventListener('dragstart', function(e) {
        draggedElement = this;
        draggedData = {
            itemId: this.dataset.itemId,
            itemType: this.dataset.itemType,
            sourceColumn: this.closest('.kanban-coluna').dataset.colunaId
        };
        
        // Adicionar classe visual
        this.classList.add('dragging');
        
        // Configurar dados do drag
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.outerHTML);
        
        console.log('📦 Iniciando drag:', draggedData);
    });
    
    item.addEventListener('dragend', function(e) {
        // Remover classe visual
        this.classList.remove('dragging');
        
        // Limpar variáveis
        draggedElement = null;
        draggedData = null;
    });
}

/**
 * Adiciona event listeners de drop a uma coluna
 */
function addDropListeners(coluna) {
    coluna.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    });
    
    coluna.addEventListener('dragenter', function(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    });
    
    coluna.addEventListener('dragleave', function(e) {
        // Verificar se realmente saiu da coluna
        if (!this.contains(e.relatedTarget)) {
            this.classList.remove('drag-over');
        }
    });
    
    coluna.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
        
        if (!draggedData) return;
        
        const targetColumnId = this.dataset.colunaId;
        const sourceColumnId = draggedData.sourceColumn;
        
        // Não fazer nada se for a mesma coluna
        if (targetColumnId === sourceColumnId) {
            console.log('🔄 Item solto na mesma coluna');
            return;
        }
        
        // Verificar limite WIP da coluna de destino
        if (!checkWipLimit(this, targetColumnId)) {
            showToast('Limite WIP atingido para esta coluna', 'error');
            return;
        }
        
        // Executar movimentação
        moveItemToColumn(draggedData, targetColumnId);
    });
}

/**
 * Verifica se a coluna pode receber mais items (WIP limit)
 */
function checkWipLimit(colunaElement, colunaId) {
    const items = colunaElement.querySelectorAll('.kanban-item');
    const currentCount = items.length;
    
    // TODO: Pegar limite WIP real do backend
    // Por enquanto, permitir até 5 items por coluna
    const wipLimit = 5;
    
    return currentCount < wipLimit;
}

/**
 * Move um item para uma nova coluna via AJAX
 */
function moveItemToColumn(itemData, targetColumnId) {
    console.log('🔄 Movendo item:', itemData, 'para coluna:', targetColumnId);
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Mostrar loading no item
    if (draggedElement) {
        draggedElement.style.opacity = '0.5';
    }
    
    fetch('/board/mover-item/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            item_id: itemData.itemId,
            item_type: itemData.itemType,
            nova_coluna_id: targetColumnId,
            nova_ordem: 0 // TODO: Calcular ordem baseada na posição do drop
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('✅ Item movido com sucesso');
            
            // Mover o elemento no DOM
            const targetColumn = document.querySelector(`[data-coluna-id="${targetColumnId}"] .space-y-3`);
            if (targetColumn && draggedElement) {
                targetColumn.appendChild(draggedElement);
                draggedElement.style.opacity = '1';
            }
            
            showToast(data.message, 'success');
            
            // Atualizar contadores das colunas
            updateColumnCounters();
            
        } else {
            console.error('❌ Erro ao mover item:', data.error);
            showToast(data.error, 'error');
            
            // Restaurar opacity
            if (draggedElement) {
                draggedElement.style.opacity = '1';
            }
        }
    })
    .catch(error => {
        console.error('❌ Erro na requisição:', error);
        showToast('Erro ao mover item. Tente novamente.', 'error');
        
        // Restaurar opacity
        if (draggedElement) {
            draggedElement.style.opacity = '1';
        }
    });
}

/**
 * Atualiza contadores de items nas colunas
 */
function updateColumnCounters() {
    const colunas = document.querySelectorAll('.kanban-coluna');
    
    colunas.forEach(coluna => {
        const items = coluna.querySelectorAll('.kanban-item');
        const counter = coluna.querySelector('.bg-gray-200');
        
        if (counter) {
            const currentText = counter.textContent;
            const parts = currentText.split('/');
            
            if (parts.length > 1) {
                // Tem limite WIP: "3 / 5"
                counter.textContent = `${items.length} / ${parts[1].trim()}`;
            } else {
                // Sem limite WIP: "3"
                counter.textContent = items.length.toString();
            }
        }
    });
}

/**
 * Adiciona evento de drag a novos items (para items criados dinamicamente)
 */
function makeItemDraggable(itemElement) {
    if (itemElement.hasAttribute('draggable')) {
        addDragListeners(itemElement);
        console.log('✅ Item tornado draggable:', itemElement.dataset.itemId);
    }
}

/**
 * Funções globais para serem chamadas pelos templates
 */
window.drag = function(e) {
    // Fallback para navegadores mais antigos
    console.log('🐭 Drag iniciado (fallback)');
};

window.allowDrop = function(e) {
    e.preventDefault();
};

window.drop = function(e) {
    e.preventDefault();
    console.log('📥 Drop executado (fallback)');
};

window.dragEnter = function(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
};

window.dragLeave = function(e) {
    e.currentTarget.classList.remove('drag-over');
};

// Inicializar quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    initializeDragAndDrop();
    
    // Observar mudanças no DOM para novos items
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1 && node.classList && node.classList.contains('kanban-item')) {
                    makeItemDraggable(node);
                }
            });
        });
    });
    
    // Observar mudanças nos containers de colunas
    const boardContainer = document.querySelector('.kanban-board');
    if (boardContainer) {
        observer.observe(boardContainer, { 
            childList: true, 
            subtree: true 
        });
    }
});

// Debug: Log quando arquivo é carregado
console.log('📁 kanban-drag-drop.js carregado');