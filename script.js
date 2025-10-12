// script.js (VERSÃO 3.0 - FINAL COM EDIÇÃO E EXCLUSÃO)
document.addEventListener('DOMContentLoaded', function() {
    
    const statsApiUrl = 'https://rastreador-de-corridas.onrender.com/api/dashboard-stats';
    const ridesApiUrl = 'https://rastreador-de-corridas.onrender.com/api/corridas';

    const totalGastoEl = document.getElementById('total-gasto');
    const totalCorridasEl = document.getElementById('total-corridas');
    const mediaCorridaEl = document.getElementById('media-corrida');
    const totalMesEl = document.getElementById('total-mes');
    const form = document.getElementById('manual-add-form');
    const formMessageEl = document.getElementById('form-message');
    const historyListEl = document.getElementById('history-list');
    const editModal = document.getElementById('edit-modal');
    const editForm = document.getElementById('edit-form');
    const closeModalBtn = document.getElementById('close-modal');

    function formatCurrency(value) { return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); }

    function updateDashboardStats() {
        fetch(statsApiUrl)
            .then(response => response.json())
            .then(data => {
                totalGastoEl.textContent = formatCurrency(data.total_gasto);
                totalCorridasEl.textContent = data.total_de_corridas;
                mediaCorridaEl.textContent = formatCurrency(data.media_por_corrida);
                totalMesEl.textContent = formatCurrency(data.total_este_mes);
            })
            .catch(error => { console.error('Erro ao buscar estatísticas:', error); [totalGastoEl, totalCorridasEl, mediaCorridaEl, totalMesEl].forEach(el => el.textContent = 'Erro'); });
    }

    function updateHistoryList() {
        fetch(ridesApiUrl)
            .then(response => response.json())
            .then(data => {
                historyListEl.innerHTML = ''; 
                if (data.length === 0) { historyListEl.innerHTML = '<p class="empty-message">Nenhuma corrida registrada ainda.</p>'; return; }
                data.forEach(ride => {
                    const item = document.createElement('div');
                    item.className = 'history-item';
                    item.dataset.rideId = ride.id;
                    const origem = ride.origem ? ride.origem.substring(0, 30) + '...' : 'N/A';
                    const destino = ride.destino ? ride.destino.substring(0, 30) + '...' : 'N/A';
                    item.innerHTML = `
                        <div class="platform">${ride.plataforma || 'N/A'}</div>
                        <div class="details">
                            <div class="date">${ride.data_corrida}</div>
                            <div class="path">${origem} → ${destino}</div>
                            <div class="payment">${ride.forma_pagamento || 'Não informado'}</div>
                        </div>
                        <div class="value">${formatCurrency(ride.valor)}</div>
                        <div class="actions">
                            <button class="edit-btn" title="Editar">✏️</button>
                            <button class="delete-btn" title="Excluir">🗑️</button>
                        </div>
                    `;
                    historyListEl.appendChild(item);
                });
            })
            .catch(error => { console.error('Erro ao buscar histórico:', error); historyListEl.innerHTML = '<p class="empty-message" style="color: #ff4d4d;">Erro ao carregar histórico.</p>'; });
    }

    function handleFormSubmit(event) {
        event.preventDefault(); 
        const formData = new FormData(form);
        const rideData = { plataforma: formData.get('plataforma'), valor: parseFloat(formData.get('valor')), data_corrida: formData.get('data') };
        formMessageEl.textContent = 'Adicionando...';
        formMessageEl.className = 'form-message';
        fetch(ridesApiUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rideData) })
            .then(response => response.json())
            .then(data => {
                if (data.id || data.mensagem?.includes('duplicada')) {
                    formMessageEl.textContent = 'Corrida adicionada com sucesso!';
                    formMessageEl.classList.add('success');
                    form.reset(); 
                    updateDashboardStats(); 
                    updateHistoryList();
                } else { throw new Error(data.erro || 'Erro desconhecido.'); }
            })
            .catch(error => { console.error('Erro ao adicionar corrida:', error); formMessageEl.textContent = `Erro: ${error.message}`; formMessageEl.classList.add('error'); });
        setTimeout(() => { formMessageEl.textContent = ''; formMessageEl.className = 'form-message'; }, 5000);
    }
    
    function handleDeleteClick(rideId) {
        if (!confirm('Tem certeza que deseja excluir esta corrida? A ação não pode ser desfeita.')) return;
        fetch(`${ridesApiUrl}/${rideId}`, { method: 'DELETE' })
            .then(response => { if (!response.ok) throw new Error('Falha ao excluir.'); return response.json(); })
            .then(() => { updateDashboardStats(); updateHistoryList(); })
            .catch(error => { console.error('Erro ao excluir corrida:', error); alert('Não foi possível excluir a corrida.'); });
    }

    function handleEditClick(rideId) {
        const item = document.querySelector(`.history-item[data-ride-id='${rideId}']`);
        if (!item) return;
        document.getElementById('edit-id').value = rideId;
        document.getElementById('edit-plataforma').value = item.querySelector('.platform').textContent;
        const valorNumerico = item.querySelector('.value').textContent.replace('R$', '').replace(/\./g, '').replace(',', '.').trim();
        document.getElementById('edit-valor').value = valorNumerico;
        document.getElementById('edit-forma-pagamento').value = item.querySelector('.payment').textContent;
        editModal.style.display = 'flex';
    }

    function handleEditFormSubmit(event) {
        event.preventDefault();
        const rideId = document.getElementById('edit-id').value;
        const updatedData = { plataforma: document.getElementById('edit-plataforma').value, valor: parseFloat(document.getElementById('edit-valor').value), forma_pagamento: document.getElementById('edit-forma-pagamento').value };
        fetch(`${ridesApiUrl}/${rideId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updatedData) })
            .then(response => { if (!response.ok) throw new Error('Falha ao salvar as alterações.'); return response.json(); })
            .then(() => { editModal.style.display = 'none'; updateDashboardStats(); updateHistoryList(); })
            .catch(error => { console.error('Erro ao editar corrida:', error); alert('Não foi possível salvar as alterações.'); });
    }

    form.addEventListener('submit', handleFormSubmit);
    historyListEl.addEventListener('click', function(event) {
        const rideId = event.target.closest('.history-item')?.dataset.rideId;
        if (!rideId) return;
        if (event.target.classList.contains('delete-btn')) handleDeleteClick(rideId);
        else if (event.target.classList.contains('edit-btn')) handleEditClick(rideId);
    });
    closeModalBtn.addEventListener('click', () => editModal.style.display = 'none');
    editModal.addEventListener('click', (event) => { if (event.target === editModal) editModal.style.display = 'none'; });
    editForm.addEventListener('submit', handleEditFormSubmit);

    updateDashboardStats();
    updateHistoryList();
});