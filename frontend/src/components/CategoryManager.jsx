import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core';
import { useDraggable, useDroppable } from '@dnd-kit/core';
import './CategoryManager.css';

// Draggable Tag Card Component
function DraggableTagCard({ tag, isEditing, editingName, onStartEdit, onSaveEdit, onCancelEdit, onDelete, onEditChange, isDragOverlay }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: tag.id,
    data: tag,
  });

  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `droppable-${tag.id}`,
    data: tag,
  });

  const combinedRef = (node) => {
    setNodeRef(node);
    setDropRef(node);
  };

  const tagClass = `category-card ${isDragging && !isDragOverlay ? 'dragging' : ''} ${isOver ? 'drag-over' : ''}`;

  return (
    <div ref={combinedRef} className={tagClass}>
      <div className="drag-handle" {...listeners} {...attributes} title="Drag to merge">
        <svg viewBox="0 0 24 24" fill="currentColor">
          <circle cx="9" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/>
          <circle cx="15" cy="5" r="1.5"/>
          <circle cx="15" cy="12" r="1.5"/>
          <circle cx="15" cy="19" r="1.5"/>
        </svg>
      </div>

      <div className="category-info">
        {isEditing ? (
          <input
            type="text"
            className="tag-edit-input"
            value={editingName}
            onChange={(e) => onEditChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSaveEdit();
              if (e.key === 'Escape') onCancelEdit();
            }}
            onBlur={onSaveEdit}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <div className="category-name" onClick={onStartEdit} title="Click to rename">
            {tag.name}
          </div>
        )}

        <div className="category-stats">
          <div className="stat-item">
            <span className="stat-value">{tag.usage_count}</span>
            <span className="stat-label">expense{tag.usage_count !== 1 ? 's' : ''}</span>
          </div>
          {tag.total_amount > 0 && (
            <div className="stat-item">
              <span className="stat-value">${tag.total_amount.toFixed(2)}</span>
              <span className="stat-label">total</span>
            </div>
          )}
        </div>
      </div>

      <div className="category-actions">
        <button
          className="icon-button edit-button"
          onClick={(e) => {
            e.stopPropagation();
            onStartEdit();
          }}
          title="Rename tag"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L21 7"/>
          </svg>
        </button>
        <button
          className="icon-button delete-tag-button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(tag.name);
          }}
          title="Delete tag"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="3,6 5,6 21,6"></polyline>
            <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
          </svg>
        </button>
      </div>
    </div>
  );
}

function TagManager({ apiUrl, onTagClick }) {
  const { getAuthHeader } = useAuth();
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [newTagName, setNewTagName] = useState('');
  const [addingTag, setAddingTag] = useState(false);
  const [deletingTags, setDeletingTags] = useState(new Set());
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [tagToDelete, setTagToDelete] = useState(null);
  const [editingTagId, setEditingTagId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [activeId, setActiveId] = useState(null);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [mergeData, setMergeData] = useState(null);
  const [merging, setMerging] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement required to start drag
      },
    })
  );

  useEffect(() => {
    fetchTags();
  }, []);

  const fetchTags = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiUrl}/api/user-tags`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) throw new Error('Failed to fetch tags');

      const data = await response.json();
      setTags(data.tags || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching tags:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addNewTag = async () => {
    const tagName = newTagName.trim();
    if (!tagName || tags.some(t => t.name === tagName)) {
      return;
    }

    try {
      setAddingTag(true);
      setError(null);

      const response = await fetch(`${apiUrl}/api/tags`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({ name: tagName }),
      });

      if (!response.ok) {
        throw new Error('Failed to create tag');
      }

      await fetchTags();
      setNewTagName('');
    } catch (err) {
      console.error('Error creating tag:', err);
      setError(err.message);
    } finally {
      setAddingTag(false);
    }
  };

  const startEditTag = (tag) => {
    setEditingTagId(tag.id);
    setEditingName(tag.name);
  };

  const saveEditTag = async () => {
    if (!editingTagId) return;

    const tag = tags.find(t => t.id === editingTagId);
    const newName = editingName.trim();

    if (!newName || newName === tag.name) {
      setEditingTagId(null);
      return;
    }

    if (tags.some(t => t.name === newName && t.id !== editingTagId)) {
      setError(`Tag "${newName}" already exists`);
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/api/tags/${encodeURIComponent(tag.name)}/rename`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({ new_name: newName }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to rename tag');
      }

      await fetchTags();
      setEditingTagId(null);
    } catch (err) {
      console.error('Error renaming tag:', err);
      setError(err.message);
    }
  };

  const cancelEditTag = () => {
    setEditingTagId(null);
    setEditingName('');
  };

  const openDeleteModal = (tagName) => {
    setTagToDelete(tagName);
    setShowDeleteModal(true);
  };

  const closeDeleteModal = () => {
    setShowDeleteModal(false);
    setTagToDelete(null);
  };

  const confirmDeleteTag = async () => {
    if (!tagToDelete) return;

    try {
      setDeletingTags(prev => new Set([...prev, tagToDelete]));
      setError(null);
      setShowDeleteModal(false);

      const response = await fetch(`${apiUrl}/api/tags/${encodeURIComponent(tagToDelete)}`, {
        method: 'DELETE',
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        throw new Error('Failed to delete tag');
      }

      await fetchTags();
    } catch (err) {
      console.error('Error deleting tag:', err);
      setError(err.message);
    } finally {
      setDeletingTags(prev => {
        const newSet = new Set(prev);
        newSet.delete(tagToDelete);
        return newSet;
      });
      setTagToDelete(null);
    }
  };

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over || active.id === over.id) {
      return; // Dropped outside or on itself
    }

    // Extract the actual droppable ID (remove "droppable-" prefix)
    const targetId = over.id.toString().replace('droppable-', '');

    if (active.id === targetId) {
      return; // Same tag
    }

    const sourceTag = tags.find(t => t.id === active.id);
    const targetTag = tags.find(t => t.id === targetId);

    if (!sourceTag || !targetTag) {
      return;
    }

    // Show merge confirmation
    setMergeData({
      source: sourceTag,
      target: targetTag,
    });
    setShowMergeModal(true);
  };

  const confirmMerge = async () => {
    if (!mergeData) return;

    try {
      setMerging(true);
      setShowMergeModal(false);

      const response = await fetch(`${apiUrl}/api/tags/merge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          source_tag: mergeData.source.name,
          target_tag: mergeData.target.name,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to merge tags');
      }

      const result = await response.json();
      console.log('Merge result:', result);

      await fetchTags();
      setMergeData(null);
    } catch (err) {
      console.error('Error merging tags:', err);
      setError(err.message);
    } finally {
      setMerging(false);
    }
  };

  const cancelMerge = () => {
    setShowMergeModal(false);
    setMergeData(null);
  };

  const filteredTags = tags.filter(tag =>
    tag.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const activeTag = activeId ? tags.find(t => t.id === activeId) : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="category-manager">
        <div className="category-header">
          <h2>Your Tags</h2>
          <p className="subtitle">
            Drag tags onto each other to merge them. Click tag names to rename.
          </p>
        </div>

        {error && (
          <div className="error-message">
            {error}
            <button onClick={() => setError(null)}>&times;</button>
          </div>
        )}

        <div className="add-category-form">
          <input
            type="text"
            placeholder="Enter new tag name..."
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addNewTag()}
            disabled={addingTag}
          />
          <button
            onClick={addNewTag}
            disabled={addingTag || !newTagName.trim() || tags.some(t => t.name === newTagName.trim())}
          >
            {addingTag ? 'Adding...' : 'Add Tag'}
          </button>
        </div>

        <div className="tag-search">
          <input
            type="text"
            placeholder="Search tags..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="tag-search-input"
          />
        </div>

        <div className="categories-list">
          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading tags...</p>
            </div>
          ) : filteredTags.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-content">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 9h-2V5h2v6zm0 4h-2v-2h2v2z"/>
                </svg>
                <h3>{tags.length === 0 ? 'No tags yet' : 'No tags found'}</h3>
                <p>{tags.length === 0 ? 'Create your first tag using the form above' : 'Try a different search term'}</p>
                {tags.length === 0 && (
                  <div className="empty-state-tips">
                    <h4>💡 Tips for using tags:</h4>
                    <ul>
                      <li>Organize expenses by category (food, travel, work)</li>
                      <li>Track different projects or clients</li>
                      <li>Drag tags onto each other to merge them</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="category-grid">
              {filteredTags.map((tag) => (
                <DraggableTagCard
                  key={tag.id}
                  tag={tag}
                  isEditing={editingTagId === tag.id}
                  editingName={editingName}
                  onStartEdit={() => startEditTag(tag)}
                  onSaveEdit={saveEditTag}
                  onCancelEdit={cancelEditTag}
                  onDelete={openDeleteModal}
                  onEditChange={setEditingName}
                  isDragOverlay={false}
                />
              ))}
            </div>
          )}
        </div>

        <DragOverlay>
          {activeTag ? (
            <div className="category-card drag-overlay">
              <div className="category-info">
                <div className="category-name">{activeTag.name}</div>
                <div className="category-stats">
                  <div className="stat-item">
                    <span className="stat-value">{activeTag.usage_count}</span>
                    <span className="stat-label">expenses</span>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </DragOverlay>

        {/* Delete Confirmation Modal */}
        {showDeleteModal && (
          <div className="modal-overlay" onClick={closeDeleteModal}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Delete Tag</h3>
              </div>
              <div className="modal-body">
                <p>Are you sure you want to delete the tag <strong>"{tagToDelete}"</strong>?</p>
                <p className="modal-warning">This will remove it from all expenses and cannot be undone.</p>
              </div>
              <div className="modal-actions">
                <button
                  className="modal-button secondary"
                  onClick={closeDeleteModal}
                  disabled={deletingTags.has(tagToDelete)}
                >
                  Cancel
                </button>
                <button
                  className="modal-button danger"
                  onClick={confirmDeleteTag}
                  disabled={deletingTags.has(tagToDelete)}
                >
                  {deletingTags.has(tagToDelete) ? 'Deleting...' : 'Delete Tag'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Merge Confirmation Modal */}
        {showMergeModal && mergeData && (
          <div className="modal-overlay" onClick={cancelMerge}>
            <div className="modal-content merge-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Merge Tags</h3>
              </div>
              <div className="modal-body">
                <div className="merge-preview">
                  <div className="merge-tag source">
                    <span className="tag-badge">{mergeData.source.name}</span>
                    <div className="tag-info">
                      {mergeData.source.usage_count} expense{mergeData.source.usage_count !== 1 ? 's' : ''}
                    </div>
                  </div>
                  <div className="merge-arrow">→</div>
                  <div className="merge-tag target">
                    <span className="tag-badge">{mergeData.target.name}</span>
                    <div className="tag-info">
                      {mergeData.target.usage_count} expense{mergeData.target.usage_count !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>
                <p>
                  This will reassign all <strong>{mergeData.source.usage_count}</strong> expense
                  {mergeData.source.usage_count !== 1 ? 's' : ''} from "<strong>{mergeData.source.name}</strong>" to "
                  <strong>{mergeData.target.name}</strong>" and delete the "{mergeData.source.name}" tag.
                </p>
                <p className="modal-warning">This action cannot be undone.</p>
              </div>
              <div className="modal-actions">
                <button
                  className="modal-button secondary"
                  onClick={cancelMerge}
                  disabled={merging}
                >
                  Cancel
                </button>
                <button
                  className="modal-button primary"
                  onClick={confirmMerge}
                  disabled={merging}
                >
                  {merging ? 'Merging...' : 'Merge Tags'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DndContext>
  );
}

export default TagManager;
