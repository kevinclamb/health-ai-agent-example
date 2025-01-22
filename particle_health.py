import json
import os
import requests
import time


class ParticleHealthClient:
    AUTH_URL = "https://sandbox.particlehealth.com/auth"
    QUERIES_URL = "https://sandbox.particlehealth.com/api/v1/queries"
    FILES_URL = "https://sandbox.particlehealth.com/api/v1/files"

    def __init__(self, client_id, client_secret):
        """
        Initialize the ParticleHealthClient with credentials.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None

    def authenticate(self):
        """
        Authenticate with the Particle Health API and obtain an access token.
        """
        headers = {
            'client-id': self.client_id,
            'client-secret': self.client_secret,
        }

        try:
            response = requests.post(self.AUTH_URL, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            self.access_token = response.json().get('access_token')
            if not self.access_token:
                raise ValueError("Access token not found in the response.")
            print("Authentication successful. Access token obtained.")
        except requests.exceptions.RequestException as e:
            print(f"Error during authentication: {e}")
        except ValueError as e:
            print(f"Error: {e}")
        return self.access_token

    def create_query(self, patient_data, use_cache=True):
        """
        Create a query for patient data. If use_cache is True, return sample response.
        """
        if use_cache:
            return self._mock_response()

        headers = self._get_headers()
        try:
            response = requests.post(self.QUERIES_URL, headers=headers, json=patient_data)
            response.raise_for_status()
            query_id = response.json().get("id")
            if not query_id:
                raise ValueError("Query ID not found in the response.")
            print(f"Query created. Query ID: {query_id}")
            return self._poll_query_status(query_id)
        except requests.exceptions.RequestException as e:
            print(f"Error creating query: {e}")
        except ValueError as e:
            print(f"Error: {e}")
        return None

    def _poll_query_status(self, query_id, interval=10):
        """
        Poll the query status until it's completed or fails.
        """
        query_url = f"{self.QUERIES_URL}/{query_id}"
        headers = self._get_headers()

        while True:
            try:
                response = requests.get(query_url, headers=headers)
                response.raise_for_status()
                status = response.json().get("status")
                print(f"Query status: {status}")

                if status == "COMPLETED":
                    print("Query completed successfully.")
                    return response.json()
                elif status == "FAILED":
                    print("Query failed.")
                    return None
                time.sleep(interval)
            except requests.exceptions.RequestException as e:
                print(f"Error checking query status: {e}")
                return None

    def download_file(self, query_id, file_id, file_path="downloaded_file.pdf"):
        """
        Download a file associated with a query.
        """
        file_url = f"{self.FILES_URL}/{query_id}/{file_id}"
        headers = self._get_headers()

        try:
            response = requests.get(file_url, headers=headers)
            response.raise_for_status()
            with open(file_path, "wb") as file:
                file.write(response.content)
            print(f"File downloaded successfully: {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            print(f"Error downloading file: {e}")
        return None

    def _get_headers(self):
        """
        Generate headers for requests with the access token.
        """
        if not self.access_token:
            raise ValueError("Access token is missing. Please authenticate first.")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    @staticmethod
    def _mock_response():
        """
        Return a mock response for cached queries.
        """
        return json.loads("""
        {
          "demographics": {
            "address_city": "Brooklyn",
            "address_lines": ["999 Dev Drive"],
            "address_state": "New York",
            "date_of_birth": "1954-12-01",
            "email": "john@doe.com",
            "family_name": "Quark",
            "gender": "MALE",
            "given_name": "Kam",
            "postal_code": "11111",
            "ssn": "123-45-6789",
            "telephone": "234-567-8910"
          },
          "files": [
            {
              "id": "file-123",
              "type": "application/pdf"
            }
          ],
          "id": "query-456",
          "state": "COMPLETE"
        }
        """)

# Example usage:
if __name__ == "__main__":
    client_id = os.getenv("PARTICLE_HEALTH_CLIENT_ID")
    client_secret = os.getenv("PARTICLE_HEALTH_SECRET_KEY")
    client = ParticleHealthClient(client_id, client_secret)

    if client.authenticate():
        # Example patient data
        patient_data = {
            "address_city": "Harwich",
            "address_lines": ["710 Batz Estate"],
            "address_state": "MA",
            "date_of_birth": "1995-09-05",
            "email": "Grant@doe.com",
            "family_name": "Bogisich",
            "gender": "Male",
            "given_name": "Grant",
            "postal_code": "02645",
            "ssn": "123-45-6789",
            "telephone": "1-234-567-8910",
        }
        query_response = client.create_query(patient_data)
        if query_response:
            query_id = query_response["id"]
            file_id = query_response["files"][0]["id"]
            client.download_file(query_id, file_id)