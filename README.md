# BIP-353 Support Tracker

This repository automatically tracks Bitcoin and Lightning Network projects that support [BIP-353](https://github.com/bitcoin/bips/blob/master/bip-0353.mediawiki), which defines Silent Payment specifications for improved privacy in Bitcoin transactions.

## Current Support Status

The support data is updated daily. View the [current support status](BIP353_SUPPORT.md) to see which projects have implemented BIP-353, which are in the process of implementing it, and which have not yet begun implementation.

## How It Works

1. A GitHub Actions workflow runs daily to scan repositories for BIP-353 mentions and implementations
2. The script checks code, documentation, issues, and pull requests
3. Results are saved as a markdown table and committed to this repository
4. The data is also available in JSON format for programmatic use

## Adding Projects

To add a project to be tracked, edit the `REPOSITORIES` list in the `bip353_tracker.py` file and submit a pull request.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue to suggest improvements or add more repositories to track.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
