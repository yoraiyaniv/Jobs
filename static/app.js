// DOM Elements
const addUserBtn = document.getElementById('addUserBtn');
const userModal = document.getElementById('userModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelBtn = document.getElementById('cancelBtn');
const userForm = document.getElementById('userForm');
const nameInput = document.getElementById('nameInput');
const emailInput = document.getElementById('emailInput');
const locationInput = document.getElementById('locationInput');
const cvInput = document.getElementById('cvInput');
const userTableBody = document.getElementById('userTableBody');
const userCount = document.getElementById('userCount');
const modalTitle = document.getElementById('modalTitle');
const deleteDialog = document.getElementById('deleteDialog');
const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
const toast = document.getElementById('toast');

let currentUserId = null;
let deleteUserId = null;

// Load users on page load
document.addEventListener('DOMContentLoaded', loadUsers);

// Event listeners
addUserBtn.addEventListener('click', openAddModal);
closeModalBtn.addEventListener('click', closeModal);
cancelBtn.addEventListener('click', closeModal);
cancelDeleteBtn.addEventListener('click', closeDeleteDialog);
userForm.addEventListener('submit', handleFormSubmit);

function openAddModal() {
    currentUserId = null;
    modalTitle.textContent = 'Add User';
    userForm.reset();
    userModal.classList.remove('hidden');
}

function closeModal() {
    userModal.classList.add('hidden');
    userForm.reset();
}

function closeDeleteDialog() {
    deleteDialog.classList.add('hidden');
    deleteUserId = null;
}

function showToast(message) {
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

async function loadUsers() {
    try {
        const response = await fetch('/api/users');
        const users = await response.json();

        userCount.textContent = users.length;

        if (users.length === 0) {
            userTableBody.innerHTML = '<tr class="border-t border-neutral-800"><td colspan="6" class="px-6 py-8 text-center text-neutral-400">No users yet</td></tr>';
            return;
        }

        userTableBody.innerHTML = users.map(user => `
            <tr class="border-t border-neutral-800 hover:bg-neutral-800">
                <td class="px-6 py-4"><a href="/jobs?user_id=${user.id}" class="text-blue-500 hover:text-blue-400 underline">${escapeHtml(user.name)}</a></td>
                <td class="px-6 py-4">${escapeHtml(user.email)}</td>
                <td class="px-6 py-4 text-neutral-400">${user.location ? escapeHtml(user.location) : '-'}</td>
                <td class="px-6 py-4">
                    ${user.cv_path ? `<a href="/cv/${encodeURIComponent(user.cv_path.split('/')[1])}" class="text-blue-500 hover:text-blue-400 underline" target="_blank">Download</a>` : '<span class="text-neutral-600">-</span>'}
                </td>
                <td class="px-6 py-4 text-neutral-400 text-sm">${new Date(user.created_at).toLocaleDateString()}</td>
                <td class="px-6 py-4 text-sm space-x-2">
                    <button onclick="analyzeJobs('${user.id}')" class="text-purple-500 hover:text-purple-400 mr-3">Analyze</button>
                    <button onclick="openEditModal('${user.id}')" class="text-blue-500 hover:text-blue-400 mr-3">Edit</button>
                    <button onclick="openDeleteDialog('${user.id}')" class="text-red-500 hover:text-red-400">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading users:', error);
        showToast('Failed to load users');
    }
}

async function openEditModal(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        const user = await response.json();

        currentUserId = userId;
        modalTitle.textContent = 'Edit User';
        nameInput.value = user.name;
        emailInput.value = user.email;
        locationInput.value = user.location || '';
        userModal.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading user:', error);
        showToast('Failed to load user');
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();

    const formData = new FormData();
    formData.append('name', nameInput.value);
    formData.append('email', emailInput.value);
    formData.append('location', locationInput.value);

    try {
        let url = '/api/users';
        let method = 'POST';

        if (currentUserId) {
            url = `/api/users/${currentUserId}`;
            method = 'PUT';
        }

        const response = await fetch(url, {
            method: method,
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.detail || 'Failed to save user');
            return;
        }

        const user = await response.json();

        // Upload CV BEFORE closing modal (which resets the form)
        if (cvInput.files.length > 0) {
            await uploadCV(user.id);
        }

        closeModal();
        showToast(currentUserId ? 'User updated' : 'User created');
        loadUsers();
    } catch (error) {
        console.error('Error saving user:', error);
        showToast('Failed to save user');
    }
}

async function uploadCV(userId) {
    const file = cvInput.files[0];
    if (!file) {
        console.log('No file selected for upload');
        return;
    }

    console.log(`Uploading CV: ${file.name} (${file.size} bytes) for user ${userId}`);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`/api/users/${userId}/cv`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            console.error('CV upload failed:', data);
            showToast(data.detail || 'Failed to upload CV');
            return;
        }

        console.log('CV uploaded successfully');
        showToast('CV uploaded successfully');
        cvInput.value = ''; // Clear the input
        loadUsers();
    } catch (error) {
        console.error('Error uploading CV:', error);
        showToast('Failed to upload CV: ' + error.message);
    }
}

function openDeleteDialog(userId) {
    deleteUserId = userId;
    deleteDialog.classList.remove('hidden');
}

confirmDeleteBtn.addEventListener('click', async () => {
    if (!deleteUserId) return;

    try {
        const response = await fetch(`/api/users/${deleteUserId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            showToast('Failed to delete user');
            return;
        }

        closeDeleteDialog();
        showToast('User deleted');
        loadUsers();
    } catch (error) {
        console.error('Error deleting user:', error);
        showToast('Failed to delete user');
    }
});

async function analyzeJobs(userId) {
    try {
        const response = await fetch(`/api/users/${userId}/analyze-jobs`, {
            method: 'POST'
        });

        const data = await response.json();

        if (!response.ok) {
            showToast(data.detail || 'Failed to start analysis');
            return;
        }

        showToast('Job analysis started in background');
    } catch (error) {
        console.error('Error starting analysis:', error);
        showToast('Failed to start analysis');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
