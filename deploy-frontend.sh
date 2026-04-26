#!/bin/bash

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  BloomWay AI - Frontend Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -d "frontend" ]; then
    echo -e "${YELLOW}Error: frontend directory not found${NC}"
    echo "Please run this script from the project root"
    exit 1
fi

# Display deployment options
echo -e "${BLUE}Choose deployment method:${NC}"
echo "1) AWS Amplify Console (Recommended - CI/CD with Git)"
echo "2) AWS Amplify CLI (Manual deployment)"
echo "3) AWS S3 + CloudFront (Manual)"
echo "4) Test locally (npm run dev)"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}AWS Amplify Console Deployment${NC}"
        echo ""
        echo "Follow these steps:"
        echo ""
        echo "1. Push your code to GitHub/GitLab/Bitbucket:"
        echo "   ${YELLOW}git add .${NC}"
        echo "   ${YELLOW}git commit -m 'Production deployment'${NC}"
        echo "   ${YELLOW}git push origin main${NC}"
        echo ""
        echo "2. Open AWS Amplify Console:"
        echo "   ${BLUE}https://console.aws.amazon.com/amplify${NC}"
        echo ""
        echo "3. Click 'New app' → 'Host web app'"
        echo ""
        echo "4. Connect your Git repository"
        echo ""
        echo "5. Amplify will auto-detect build settings from amplify.yml"
        echo ""
        echo "6. Deploy and get your URL!"
        echo ""
        echo -e "${GREEN}✓ Configuration files ready:${NC}"
        echo "  - amplify.yml (build configuration)"
        echo "  - frontend/public/_redirects (SPA routing)"
        echo "  - frontend/.env (API endpoint configured)"
        echo ""
        ;;
    
    2)
        echo ""
        echo -e "${GREEN}AWS Amplify CLI Deployment${NC}"
        echo ""
        
        # Check if Amplify CLI is installed
        if ! command -v amplify &> /dev/null; then
            echo "Installing Amplify CLI..."
            npm install -g @aws-amplify/cli
        fi
        
        echo "Initializing Amplify..."
        cd frontend
        
        if [ ! -d "amplify" ]; then
            echo "Running amplify init..."
            amplify init
        fi
        
        echo "Adding hosting..."
        amplify add hosting
        
        echo "Publishing..."
        amplify publish
        
        echo ""
        echo -e "${GREEN}✓ Deployment complete!${NC}"
        ;;
    
    3)
        echo ""
        echo -e "${GREEN}AWS S3 + CloudFront Deployment${NC}"
        echo ""
        
        BUCKET_NAME="bloomway-frontend-prod"
        
        echo "Creating S3 bucket..."
        aws s3 mb s3://$BUCKET_NAME --region us-east-1 || true
        
        echo "Configuring static website hosting..."
        aws s3 website s3://$BUCKET_NAME \
            --index-document index.html \
            --error-document index.html
        
        echo "Uploading build..."
        aws s3 sync frontend/dist/ s3://$BUCKET_NAME/ \
            --delete \
            --cache-control "public, max-age=31536000, immutable" \
            --exclude "index.html"
        
        aws s3 cp frontend/dist/index.html s3://$BUCKET_NAME/index.html \
            --cache-control "no-cache, no-store, must-revalidate"
        
        echo "Making bucket public..."
        cat > /tmp/bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF
        
        aws s3api put-bucket-policy \
            --bucket $BUCKET_NAME \
            --policy file:///tmp/bucket-policy.json
        
        echo ""
        echo -e "${GREEN}✓ Deployment complete!${NC}"
        echo ""
        echo "Website URL: http://$BUCKET_NAME.s3-website-us-east-1.amazonaws.com"
        echo ""
        echo "To add CloudFront CDN, run:"
        echo "  aws cloudfront create-distribution --origin-domain-name $BUCKET_NAME.s3-website-us-east-1.amazonaws.com"
        ;;
    
    4)
        echo ""
        echo -e "${GREEN}Starting local development server...${NC}"
        echo ""
        cd frontend
        npm run dev
        ;;
    
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Done!${NC}"
echo -e "${BLUE}========================================${NC}"
