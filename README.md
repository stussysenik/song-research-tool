# Song Research Tool

A Python-based tool for analyzing and managing song playlists. This tool helps users research and organize their music collections efficiently.

## Features

- Playlist management
- Song analysis
- Data export capabilities

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the main script: `python download_playlist.py`

## Learning: Git Authentication and Troubleshooting

This project provided valuable lessons in Git authentication and remote repository management. Here's what we learned:

### Setting up SSH Authentication

1. Generate an SSH key:
```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

2. Copy the public key:
```bash
# Install xclip if needed
sudo apt-get install xclip
# Copy the key to clipboard
cat ~/.ssh/id_ed25519_pop_os.pub | xclip -selection clipboard
```

3. Add the key to GitHub:
   - Go to GitHub Settings → SSH Keys
   - Click "New SSH Key"
   - Paste your key and give it a descriptive name

4. Change remote URL from HTTPS to SSH:
```bash
git remote set-url origin git@github.com:username/repository.git
```

### Troubleshooting Push Rejections

When encountering the "rejected (fetch first)" error:

1. The error means the remote has changes you don't have locally
2. Solution steps:
```bash
# Fetch remote changes
git fetch origin

# Pull with rebase to keep history clean
git pull --rebase origin main

# Push your changes
git push origin main
```

### Key Learnings

1. Always set up SSH keys for secure authentication
2. Use `xclip` for easy key copying
3. When push is rejected:
   - Fetch first to see remote changes
   - Use rebase to maintain clean history
   - Then push your changes

## Contributing

Feel free to submit issues and pull requests.

## License

This project is open source and available under the MIT License. 