import hashlib
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# --- Fix for Windows console Unicode errors ---
# Forces stdout to use UTF-8 (so symbols or emojis won't crash)
sys.stdout.reconfigure(encoding='utf-8')

# --- Configuration ---
HASH_ALGORITHM = "sha256"
BLOCKCHAIN_FILE = "blockchain_data.json"
DEMO_FILE_PATH = "important_document.txt"
MINING_DIFFICULTY = 2  # Number of leading zeros required


class Block:
    """Represents a single block in the blockchain, storing file metadata."""

    def __init__(self, index: int, previous_hash: str, timestamp: float, data: Dict[str, Any], difficulty: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.difficulty = difficulty
        self.hash = ""

        # Mine the block if difficulty is set
        if difficulty > 0:
            self.mine_block()
        else:
            self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculates the hash for the current block's contents."""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self):
        """Proof-of-work mining: find a hash with required leading zeros."""
        target = "0" * self.difficulty
        print(f"[⛏️] Mining block {self.index}... (difficulty: {self.difficulty})", end="", flush=True)

        start_time = time.time()
        while True:
            self.hash = self.calculate_hash()
            if self.hash[:self.difficulty] == target:
                elapsed = time.time() - start_time
                print(f" ✓ Mined in {elapsed:.2f}s (nonce: {self.nonce})")
                break
            self.nonce += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(block_dict: Dict[str, Any]) -> 'Block':
        """Create block from dictionary using standard initialization."""
        # Create a new instance with default values
        block = Block(
            index=block_dict["index"],
            previous_hash=block_dict["previous_hash"],
            timestamp=block_dict["timestamp"],
            data=block_dict["data"],
            difficulty=block_dict.get("difficulty", 0)
        )
        # Set the nonce and hash from the dictionary
        block.nonce = block_dict["nonce"]
        block.hash = block_dict["hash"]
        return block

    def __repr__(self) -> str:
        """Readable representation of the block data."""
        dt = datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"\n{'='*60}\n"
            f"Block #{self.index}\n"
            f"{'='*60}\n"
            f"Timestamp:     {dt}\n"
            f"File:          {self.data.get('filename', 'N/A')}\n"
            f"Uploader ID:   {self.data.get('uploader_id', 'N/A')}\n"
            f"Action:        {self.data.get('action', 'N/A')}\n"
            f"File Hash:     {self.data.get('file_hash', 'N/A')[:20]}...\n"
            f"File Size:     {self.data.get('file_size', 'N/A')} bytes\n"
            f"Previous Hash: {self.previous_hash[:20]}...\n"
            f"Block Hash:    {self.hash[:20]}...\n"
            f"Nonce:         {self.nonce}\n"
            f"{'='*60}"
        )


class Blockchain:
    """Manages the chain of blocks and provides integrity checks."""

    def __init__(self, difficulty: int = MINING_DIFFICULTY):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_verifications: List[Dict[str, Any]] = []

    def create_genesis_block(self):
        """Creates the initial block of the chain (index 0)."""
        genesis_data = {
            "note": "Genesis Block - Blockchain Initialized",
            "action": "GENESIS",
            "timestamp": datetime.now().isoformat(),
            "uploader_id": "system"
        }
        genesis_block = Block(
            index=0,
            previous_hash="0" * 64,
            timestamp=time.time(),
            data=genesis_data,
            difficulty=0
        )
        self.chain.append(genesis_block)
        print("\n[🔗] Blockchain initialized with Genesis Block")

    def get_latest_block(self) -> Block:
        """Returns the most recently added block."""
        return self.chain[-1] if self.chain else None

    def add_block(self, file_data: Dict[str, Any]) -> bool:
        """Creates a new block containing file metadata and adds it to the chain."""
        try:
            latest_block = self.get_latest_block()
            new_index = latest_block.index + 1
            new_timestamp = time.time()

            new_block = Block(
                index=new_index,
                previous_hash=latest_block.hash,
                timestamp=new_timestamp,
                data=file_data,
                difficulty=self.difficulty
            )

            self.chain.append(new_block)
            print(f"[✅] Block {new_index} added: {file_data.get('action', 'ACTION')} - {file_data['filename']}")
            return True

        except Exception as e:
            print(f"[❌] Error adding block: {e}")
            return False

    def find_latest_block_for_file(self, filename: str) -> Optional[Block]:
        """Find the most recent block containing a specific file."""
        for block in reversed(self.chain):
            if block.data.get('filename') == filename:
                return block
        return None

    def get_file_history(self, filename: str) -> List[Block]:
        """Get all blocks related to a specific file."""
        return [block for block in self.chain if block.data.get('filename') == filename]

    def is_valid(self) -> bool:
        """Verifies the integrity of the entire chain by checking hash links."""
        print("\n[🔍] Validating blockchain integrity...")

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.hash != current_block.calculate_hash():
                print(f"[❌] VALIDATION FAILED: Block {i} hash is corrupted")
                return False

            if current_block.previous_hash != previous_block.hash:
                print(f"[❌] VALIDATION FAILED: Block {i} lost link to Block {i-1}")
                return False

            if current_block.difficulty > 0:
                target = "0" * current_block.difficulty
                if not current_block.hash.startswith(target):
                    print(f"[❌] VALIDATION FAILED: Block {i} doesn't meet difficulty requirement")
                    return False

        print("[✅] Blockchain validation successful")
        return True

    def save_chain(self, filename: str = BLOCKCHAIN_FILE):
        """Persist blockchain to disk."""
        try:
            chain_data = {
                "difficulty": self.difficulty,
                "blocks": [block.to_dict() for block in self.chain]
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(chain_data, f, indent=2)
            print(f"[💾] Blockchain saved to '{filename}'")
            return True
        except Exception as e:
            print(f"[❌] Error saving blockchain: {e}")
            return False

    def load_chain(self, filename: str = BLOCKCHAIN_FILE) -> bool:
        """Load blockchain from disk."""
        try:
            if not os.path.exists(filename):
                print(f"[⚠️] No existing blockchain found at '{filename}'")
                return False

            with open(filename, 'r', encoding='utf-8') as f:
                chain_data = json.load(f)

            self.difficulty = chain_data.get("difficulty", MINING_DIFFICULTY)
            self.chain = [Block.from_dict(block_dict) for block_dict in chain_data["blocks"]]

            print(f"[📂] Blockchain loaded from '{filename}' ({len(self.chain)} blocks)")
            return True
        except Exception as e:
            print(f"[❌] Error loading blockchain: {e}")
            return False

    def display_chain(self):
        """Display all blocks in the chain."""
        print(f"\n{'#'*60}")
        print(f"BLOCKCHAIN EXPLORER - Total Blocks: {len(self.chain)}")
        print(f"{'#'*60}")
        for block in self.chain:
            print(block)

    def get_statistics(self) -> Dict[str, Any]:
        """Get blockchain statistics."""
        files_tracked = set()
        actions = {}
        uploaders = set()

        for block in self.chain[1:]:
            filename = block.data.get('filename')
            if filename:
                files_tracked.add(filename)
            action = block.data.get('action', 'UNKNOWN')
            actions[action] = actions.get(action, 0) + 1
            uploader = block.data.get('uploader_id')
            if uploader:
                uploaders.add(uploader)

        return {
            "total_blocks": len(self.chain),
            "files_tracked": len(files_tracked),
            "unique_uploaders": len(uploaders),
            "actions": actions,
            "difficulty": self.difficulty
        }


class FileIntegrityManager:
    """Manages file operations and integrity verification."""

    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain

    @staticmethod
    def get_file_hash(filepath: str) -> Optional[str]:
        """Calculates the SHA-256 hash of a file's content."""
        try:
            h = hashlib.sha256()
            with open(filepath, 'rb') as file:
                for byte_block in iter(lambda: file.read(4096), b""):
                    h.update(byte_block)
            return h.hexdigest()
        except FileNotFoundError:
            print(f"[❌] File not found: '{filepath}'")
            return None
        except Exception as e:
            print(f"[❌] Error reading file: {e}")
            return None

    @staticmethod
    def get_file_metadata(filepath: str) -> Optional[Dict[str, Any]]:
        """Get file metadata including size and modification time."""
        try:
            stat = os.stat(filepath)
            return {"size": stat.st_size, "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()}
        except Exception as e:
            print(f"[❌] Error getting file metadata: {e}")
            return None

    def register_file(self, filepath: str, uploader_id: str = "anonymous", action: str = "FILE_REGISTERED") -> bool:
        """Register a new file or update existing file in blockchain."""
        print(f"\n[📝] Registering file: '{filepath}' (Uploader: {uploader_id})")

        file_hash = self.get_file_hash(filepath)
        if not file_hash:
            return False

        metadata = self.get_file_metadata(filepath)
        if not metadata:
            return False

        file_data = {
            "filename": filepath,
            "file_hash": file_hash,
            "file_size": metadata["size"],
            "uploader_id": uploader_id,
            "action": action,
            "timestamp": datetime.now().isoformat()
        }

        return self.blockchain.add_block(file_data)

    def verify_file_integrity(self, filepath: str) -> bool:
        """Verify file integrity against blockchain records."""
        print(f"\n[🔍] Verifying integrity of '{filepath}'...")

        block = self.blockchain.find_latest_block_for_file(filepath)
        if not block:
            print(f"[⚠️] No blockchain record found for '{filepath}'")
            return False

        stored_hash = block.data.get('file_hash')
        stored_size = block.data.get('file_size')
        uploader_id = block.data.get('uploader_id', 'unknown')

        current_hash = self.get_file_hash(filepath)
        if not current_hash:
            return False

        metadata = self.get_file_metadata(filepath)
        if not metadata:
            return False

        print(f"\n📊 Verification Report:")
        print(f"   Uploader ID:    {uploader_id}")
        print(f"   Recorded Hash:  {stored_hash[:30]}...")
        print(f"   Current Hash:   {current_hash[:30]}...")
        print(f"   Recorded Size:  {stored_size} bytes")
        print(f"   Current Size:   {metadata['size']} bytes")
        print(f"   Block Index:    {block.index}")
        print(f"   Block Time:     {datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")

        if current_hash == stored_hash:
            print("\n✅ [SUCCESS] File integrity verified - No tampering detected")
            return True
        else:
            print("\n❌ [FAILURE] File integrity compromised - File has been modified!")
            return False


# --- Utility Functions ---

def setup_demo_file(content: str, filepath: str = DEMO_FILE_PATH):
    try:
        with open(filepath, "w", encoding='utf-8') as f:
            f.write(content)
        print(f"[📄] Demo file created: '{filepath}'")
        return True
    except Exception as e:
        print(f"[❌] Error creating demo file: {e}")
        return False


def modify_demo_file(content: str, filepath: str = DEMO_FILE_PATH):
    try:
        with open(filepath, "a", encoding='utf-8') as f:
            f.write(content)
        print(f"[⚠️] File modified: '{filepath}'")
        return True
    except Exception as e:
        print(f"[❌] Error modifying file: {e}")
        return False


def display_menu():
    print("\n" + "=" * 60)
    print("BLOCKCHAIN FILE INTEGRITY SYSTEM")
    print("=" * 60)
    print("1. Register a new file")
    print("2. Verify file integrity")
    print("3. View file history")
    print("4. Display blockchain")
    print("5. Validate blockchain")
    print("6. Show statistics")
    print("7. Save blockchain")
    print("8. Run demo simulation")
    print("9. Exit")
    print("=" * 60)


def interactive_mode(blockchain: Blockchain, manager: FileIntegrityManager):
    while True:
        display_menu()
        choice = input("\nEnter your choice (1-9): ").strip()

        if choice == "1":
            filepath = input("Enter file path to register: ").strip()
            if os.path.exists(filepath):
                uploader_id = input("Enter uploader ID (press Enter for 'anonymous'): ").strip() or "anonymous"
                manager.register_file(filepath, uploader_id)
            else:
                print(f"[❌] File not found: '{filepath}'")

        elif choice == "2":
            filepath = input("Enter file path to verify: ").strip()
            manager.verify_file_integrity(filepath)

        elif choice == "3":
            filepath = input("Enter file path: ").strip()
            history = blockchain.get_file_history(filepath)
            if not history:
                print(f"[⚠️] No history found for '{filepath}'")
            else:
                print(f"\n📜 File History for '{filepath}':")
                for block in history:
                    dt = datetime.fromtimestamp(block.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    uploader = block.data.get('uploader_id', 'unknown')
                    print(f"   Block {block.index} | {dt} | {block.data.get('action')} | Uploader: {uploader}")

        elif choice == "4":
            blockchain.display_chain()

        elif choice == "5":
            blockchain.is_valid()

        elif choice == "6":
            stats = blockchain.get_statistics()
            print(f"\n📊 Blockchain Statistics:")
            print(f"   Total Blocks:      {stats['total_blocks']}")
            print(f"   Files Tracked:     {stats['files_tracked']}")
            print(f"   Unique Uploaders:  {stats['unique_uploaders']}")
            print(f"   Difficulty:        {stats['difficulty']}")
            print(f"   Actions:           {stats['actions']}")

        elif choice == "7":
            blockchain.save_chain()

        elif choice == "8":
            run_demo_simulation(blockchain, manager)

        elif choice == "9":
            print("\n[👋] Saving and exiting...")
            blockchain.save_chain()
            break

        else:
            print("[❌] Invalid choice. Please try again.")


def run_demo_simulation(blockchain: Blockchain, manager: FileIntegrityManager):
    print("\n" + "=" * 60)
    print("STARTING DEMO SIMULATION")
    print("=" * 60)

    # Phase 1: Create and register original file
    print("\n📝 PHASE 1: Creating and registering original file")
    print("-" * 60)
    initial_content = "This is the original, secure data.\nNo unauthorized changes allowed!\nTimestamp: " + datetime.now().isoformat()
    setup_demo_file(initial_content)
    manager.register_file(DEMO_FILE_PATH, "demo_user", "FILE_CREATED")

    # Phase 2: Verify before tampering
    print("\n🔍 PHASE 2: Verification BEFORE Tampering")
    print("-" * 60)
    manager.verify_file_integrity(DEMO_FILE_PATH)

    # Phase 3: Simulate unauthorized modification
    print("\n⚠️ PHASE 3: Simulating Unauthorized Modification")
    print("-" * 60)
    time.sleep(1)
    modify_demo_file("\n\n-- UNAUTHORIZED ADDITION --\nSecret data injected!")
    print("[!] Note: The modified file has NOT been re-registered in the blockchain")

    # Phase 4: Verify after tampering
    print("\n🔍 PHASE 4: Verification AFTER Tampering")
    print("-" * 60)
    manager.verify_file_integrity(DEMO_FILE_PATH)

    # Phase 5: Register the modified file (proper procedure)
    print("\n📝 PHASE 5: Registering the modified file (proper procedure)")
    print("-" * 60)
    manager.register_file(DEMO_FILE_PATH, "demo_user", "FILE_MODIFIED")

    # Phase 6: Verify after proper registration
    print("\n🔍 PHASE 6: Verification after proper registration")
    print("-" * 60)
    manager.verify_file_integrity(DEMO_FILE_PATH)

    # Phase 7: Show file history
    print("\n📜 PHASE 7: Displaying complete file history")
    print("-" * 60)
    history = blockchain.get_file_history(DEMO_FILE_PATH)
    for block in history:
        dt = datetime.fromtimestamp(block.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        print(f"   Block {block.index} | {dt} | {block.data.get('action')} | Uploader: {block.data.get('uploader_id')}")

    # Phase 8: Validate blockchain
    print("\n🔒 PHASE 8: Blockchain Validation")
    print("-" * 60)
    blockchain.is_valid()

    print("\n✅ Demo simulation completed!")


# --- Main Entry Point ---
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("BLOCKCHAIN-BASED FILE INTEGRITY SYSTEM")
    print("=" * 60)

    security_chain = Blockchain(difficulty=MINING_DIFFICULTY)

    if not security_chain.load_chain():
        security_chain.create_genesis_block()
        security_chain.save_chain()

    file_manager = FileIntegrityManager(security_chain)

    try:
        interactive_mode(security_chain, file_manager)
    except KeyboardInterrupt:
        print("\n\n[⚠️] Interrupted by user")
        security_chain.save_chain()
    except Exception as e:
        print(f"\n[❌] Unexpected error: {e}")
        security_chain.save_chain()