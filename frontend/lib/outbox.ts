export type OutboxItem = {
  id: string;
  path: string;
  body: unknown;
  createdAt: string;
  attempts: number;
  lastError?: string;
};

const DB = "predictrx-offline";
const STORE = "chart-outbox";

function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) {
        request.result.createObjectStore(STORE, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function transaction<T>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await database();
  try {
    return await new Promise<T>((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const request = operation(tx.objectStore(STORE));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

export async function enqueue(path: string, body: unknown): Promise<OutboxItem> {
  const item: OutboxItem = {
    id: crypto.randomUUID(),
    path,
    body,
    createdAt: new Date().toISOString(),
    attempts: 0,
  };
  await transaction("readwrite", (store) => store.put(item));
  return item;
}

export async function outboxItems(): Promise<OutboxItem[]> {
  const items = await transaction<OutboxItem[]>("readonly", (store) => store.getAll());
  return items.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

export async function removeOutbox(id: string): Promise<void> {
  await transaction("readwrite", (store) => store.delete(id));
}

export async function updateOutbox(item: OutboxItem): Promise<void> {
  await transaction("readwrite", (store) => store.put(item));
}

export async function flushOutbox(submit: (item: OutboxItem) => Promise<void>): Promise<{ sent: number; pending: number }> {
  const items = await outboxItems();
  let sent = 0;
  for (const item of items) {
    try {
      await submit(item);
      await removeOutbox(item.id);
      sent += 1;
    } catch (error) {
      await updateOutbox({
        ...item,
        attempts: item.attempts + 1,
        lastError: error instanceof Error ? error.message : String(error),
      });
      break; // Preserve chart order and stop hammering an unavailable server.
    }
  }
  return { sent, pending: (await outboxItems()).length };
}
